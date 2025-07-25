from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, make_response, abort
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, date
import os
import utility
import yaml
from sqlalchemy.orm import sessionmaker
import base64
from werkzeug.utils import secure_filename
from markdown2 import Markdown
from flask import send_from_directory
from utility import save_image, delete_image
from dotenv import load_dotenv
from utils.config_utils import load_config, update_config, get_config_for_settings, get_section_title, get_section_icon, reset_config_to_defaults

from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image as RLImage, PageBreak, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, cm
from reportlab.lib import colors
from reportlab.lib.enums import TA_JUSTIFY, TA_CENTER, TA_LEFT
from reportlab.platypus.flowables import HRFlowable
import io
import os
import markdown
import re
from PIL import Image as PILImage

from datetime import datetime

import sys
parent_dir = ".."
sys.path.append(parent_dir)
import models.base
import models.artifact
import models.type
import models.config

# Fix for template rendering
import sys
sys.path.append('/app')

load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('FLASK_SECRET_KEY')

# Create instance directory if it doesn't exist
instance_path = '/app/instance'
os.makedirs(instance_path, exist_ok=True)

# Declare config as global at module level
config = None

# Load config from database instead of YAML
def initialize_config():
    global config
    config = load_config()
    
    # Ensure default_type configuration exists in database
    from migrate_default_type import ensure_all_general_configs
    ensure_all_general_configs()

# Initialize config
initialize_config()

# Create database if it doesn't exist
utility.create_database(config=config)
Session = sessionmaker(bind=models.base.engine)
session = Session()
Artifact = models.artifact.Artifact
Type = models.type.Type

# Make date available in templates
@app.context_processor
def inject_date():
    return {'today': date.today()}

@app.context_processor
def inject_helpers():
    return dict(
        get_section_title=get_section_title,
        get_section_icon=get_section_icon,
        today=date.today(),
        config=config
    )

# Create markdown renderer
markdowner = Markdown(extras=["tables", "fenced-code-blocks"])

@app.template_filter('markdown')
def markdown_filter(text):
    return markdowner.convert(text)

@app.route('/settings', methods=['GET', 'POST'])
def settings():
    global config
    
    if request.method == 'POST':
        # Check if this is a reset request
        if 'reset_defaults' in request.form:
            try:
                if reset_config_to_defaults():
                    flash('Configuration reset to default values successfully!', 'success')
                    # Reload config
                    config = load_config()
                else:
                    flash('Error resetting configuration to defaults.', 'error')
            except Exception as e:
                flash(f'Error resetting configuration: {str(e)}', 'error')
            
            return redirect(url_for('settings'))
        
        # Normal settings update
        try:
            # Get all form data
            updates = {}
            for key in request.form:
                if key == 'reset_defaults':  # Skip reset button
                    continue
                    
                value = request.form[key]
                
                # Convert values to appropriate types based on key patterns
                if key.endswith(('_port', '_size', '_days', '_hours', '_notifications', '_interval')) or key.split('.')[-1] in ['max_file_size', 'smtp_port', 'notification_days', 'max_notifications', 'notification_interval', 'cleanup_threshold_hours']:
                    value = int(value)
                elif value.lower() in ('true', 'false'):
                    value = value.lower() == 'true'
                elif key == 'type' or key.endswith('.allowed_extensions'):
                    # Handle arrays
                    value = [t.strip() for t in value.split(',') if t.strip()]
                
                updates[key] = value
            
            # Update each config item
            success_count = 0
            for key, value in updates.items():
                if update_config(key, value):
                    success_count += 1
            
            if success_count > 0:
                flash(f'Successfully updated {success_count} configuration(s)!', 'success')
                # Reload config
                config = load_config()
            else:
                flash('No configurations were updated.', 'error')
                
        except Exception as e:      
            flash(f'Error updating configuration: {str(e)}', 'error')
        
        return redirect(url_for('index'))
    
    # Get all config items for display
    config_items = get_config_for_settings()
    return render_template('settings.html', config_items=config_items)

@app.route('/')
def index():
    type_filter = request.args.get('type', '')  # Changed to empty string default
    show_all = request.args.get('type') == 'all'
    
    # Get default type from config if no type filter is specified and not showing all
    if not type_filter and not show_all:
        default_type_name = config.get('general', {}).get('default_type', 'Token')
        # Find the ID of the default type
        default_type = session.query(Type).filter(Type.name == default_type_name).first()
        if default_type:
            type_filter = str(default_type.id)
    
    # Start with base query - no search filtering on index page
    query = session.query(Artifact)
    
    # Apply type filter only if specifically selected and not showing all
    if type_filter and not show_all:
        query = query.filter(Artifact.type_id == type_filter)
    
    # Get final results
    artifacts = query.order_by(Artifact.expiry_date.asc()).filter(Artifact.deleted == False).all()
    
    # Get types for dropdown
    types = session.query(Type).all()
    types_dict = {t.id: t.name for t in types}
    
    return render_template('index.html', 
                         artifacts=artifacts,
                         type_filter=type_filter if not show_all else '',
                         show_all=show_all,
                         today=date.today(),
                         types=types,
                         config=config,
                         types_dict=types_dict)

@app.route('/search')
def search():
    search_query = request.args.get('search', '').strip()
    type_filter = request.args.get('type', '')
    
    # Start with base query
    query = session.query(Artifact).filter(Artifact.deleted == False)
    
    # Apply search filter if present
    if search_query:
        name_results = query.filter(Artifact.name.ilike(f'%{search_query}%'))
        content_results = query.filter(Artifact.content.ilike(f'%{search_query}%'))
        query = name_results.union(content_results)
    else:
        # If no search query, return empty results to encourage searching
        query = query.filter(Artifact.id == -1)  # This will return no results
    
    # Apply type filter only if specifically selected
    if type_filter:
        query = query.filter(Artifact.type_id == type_filter)
    
    # Get final results
    artifacts = query.order_by(Artifact.expiry_date.asc()).all()
    
    # Get types for dropdown
    types = session.query(Type).all()
    types_dict = {t.id: t.name for t in types}
    
    return render_template('search.html', 
                         artifacts=artifacts,
                         search_query=search_query,
                         type_filter=type_filter,
                         today=date.today(),
                         types=types,
                         config=config,
                         types_dict=types_dict)


@app.route('/add', methods=['GET', 'POST'])
def add_artifact():
    if request.method == 'POST':
        try:
            # Get form data
            name = request.form['name']
            type_id = request.form['artifact_type']
            content = request.form['content']
            expiry_date_str = request.form.get('expiry_date')
            
            # Handle expiry date
            expiry_date = None
            if expiry_date_str:
                expiry_date = datetime.strptime(expiry_date_str, '%Y-%m-%d').date()
            
            # Handle image uploads
            files = request.files.getlist('images[]')
            images_data = []
            
            for file in files:
                if file and file.filename:
                    if not file.content_type.startswith('image/'):
                        raise ValueError(f"Invalid file type: {file.filename}")
                    
                    if file.content_length > config['storage']['max_file_size']:
                        raise ValueError(f"File too large: {file.filename}")
                    
                    # Save image and store metadata
                    relative_path = save_image(file, config)
                    images_data.append({
                        'name': file.filename,
                        'path': relative_path
                    })
            
            # Create artifact with image metadata
            artifact = Artifact(
                name=request.form['name'],
                type_id=request.form['artifact_type'],
                content=request.form['content'],
                expiry_date=expiry_date,
                images=images_data
            )
            
            session.add(artifact)
            session.commit()
            
            flash('Artifact created successfully!', 'success')
            return redirect(url_for('index'))
            
        except Exception as e:
            # Delete any saved images if artifact creation fails
            for image in images_data:
                delete_image(image['path'])
            flash(str(e), 'error')
            session.rollback()
    
    # GET request - show form
    types = session.query(Type).all()
    
    # Get default type from config
    default_type_name = config.get('general', {}).get('default_type', 'Token')
    default_type_id = None
    
    # Find the ID of the default type
    for type_obj in types:
        if type_obj.name == default_type_name:
            default_type_id = type_obj.id
            break
    
    return render_template('add_artifact.html', types=types, default_type_id=default_type_id)

@app.route('/delete/<int:artifact_id>', methods=['POST'])
def delete_artifact(artifact_id):
    artifact = session.query(Artifact).get(artifact_id)
    if artifact:
        # Soft delete instead of hard delete
        artifact.soft_delete()
        session.commit()
        flash('Artifact has been moved to trash', 'info')
    return redirect(url_for('index'))

@app.route('/update/<int:artifact_id>', methods=['GET', 'POST'])
def update_artifact(artifact_id):
    artifact = session.query(Artifact).filter(Artifact.id==artifact_id).first()
    if request.method == 'POST':
        try:
            # Update basic info
            artifact.name = request.form['name']
            artifact.content = request.form['content']
            artifact.type_id = request.form['artifact_type']
            
            # Handle expiry date
            expiry_date = None
            if request.form.get('expiry_date'):
                expiry_date = datetime.strptime(request.form['expiry_date'], '%Y-%m-%d').date()
            artifact.expiry_date = expiry_date

            # Initialize images array if None
            if artifact.images is None:
                artifact.images = []
            else:
                # Convert to list if it's not already
                artifact.images = list(artifact.images)

            # Handle removed images
            removed_images = request.form.get('removed_images', '').split(',')
            if removed_images[0]:
                for img in artifact.images[:]:
                    if img['name'] in removed_images:
                        delete_image(img['path'])
                        artifact.images.remove(img)

            # Handle new images
            files = request.files.getlist('images[]')
            for file in files:
                if file and file.filename:
                    if not file.content_type.startswith('image/'):
                        raise ValueError(f"Invalid file type: {file.filename}")
                    
                    if file.content_length > config['storage']['max_file_size']:
                        raise ValueError(f"File too large: {file.filename}")
                    
                    # Save new image
                    relative_path = save_image(file, config)
                    artifact.images.append({
                        'name': file.filename,
                        'path': relative_path
                    })
            
            session.add(artifact)
            session.commit()
            
            flash('Artifact updated successfully!', 'success')
            return redirect(url_for('index'))
            
        except Exception as e:
            flash(str(e), 'error')
            session.rollback()

    types = session.query(Type).all()
    return render_template('update_artifact.html', artifact=artifact, types=types)

@app.route('/artifact/<int:artifact_id>')
def artifact_detail(artifact_id):
    artifact = session.query(Artifact).filter(Artifact.id==artifact_id).first()
    if not artifact:
        flash('Artifact not found!', 'error')
        return redirect(url_for('index'))
    
    # Get type name
    type_obj = session.query(Type).filter(Type.id==artifact.type_id).first()
    type_name = type_obj.name if type_obj else 'Unknown'
    
    # Calculate status
    if artifact.expiry_date is None:
        days_until_expiry = None
        status_badge = "bg-secondary"
        status_text = "No Expiry Date"
        status_icon = "fas fa-calendar-times"
    else:
        days_until_expiry = (artifact.expiry_date - date.today()).days
        if artifact.is_expired():
            status_badge = "bg-danger"
            status_text = "Expired"
            status_icon = "fas fa-times-circle"
        elif days_until_expiry <= 14:
            status_badge = "bg-warning text-dark"
            status_text = "Expires Soon"
            status_icon = "fas fa-exclamation-triangle"
        else:
            status_badge = "bg-success"
            status_text = "Active"
            status_icon = "fas fa-check-circle"
    
    return render_template('artifact_detail.html', 
                         artifact=artifact,
                         type_name=type_name,
                         days_until_expiry=days_until_expiry,
                         status_badge=status_badge,
                         status_text=status_text,
                         status_icon=status_icon,
                         config=config)


@app.route('/static/uploads/<path:filename>')
def serve_image(filename):
    return send_from_directory(config['storage']['image_path'], filename)

def clean_markdown_for_pdf(text):
    """Convert markdown to PDF-friendly text with basic formatting"""
    if not text:
        return ""
    
    # Convert markdown to HTML first
    html = markdown.markdown(text, extensions=['tables', 'fenced_code'])
    
    # Clean HTML tags for reportlab
    html = re.sub(r'<h1>(.*?)</h1>', r'<para fontSize="18" spaceAfter="12"><b>\1</b></para>', html)
    html = re.sub(r'<h2>(.*?)</h2>', r'<para fontSize="16" spaceAfter="10"><b>\1</b></para>', html)
    html = re.sub(r'<h3>(.*?)</h3>', r'<para fontSize="14" spaceAfter="8"><b>\1</b></para>', html)
    html = re.sub(r'<h4>(.*?)</h4>', r'<para fontSize="12" spaceAfter="6"><b>\1</b></para>', html)
    html = re.sub(r'<strong>(.*?)</strong>', r'<b>\1</b>', html)
    html = re.sub(r'<em>(.*?)</em>', r'<i>\1</i>', html)
    html = re.sub(r'<code>(.*?)</code>', r'<font name="Courier">\1</font>', html)
    html = re.sub(r'<pre><code>(.*?)</code></pre>', r'<para backColor="#f0f0f0" borderPadding="10"><font name="Courier">\1</font></para>', html, flags=re.DOTALL)
    html = re.sub(r'<blockquote>(.*?)</blockquote>', r'<para leftIndent="20" borderWidth="2" borderColor="#3498db" borderPadding="10"><i>\1</i></para>', html, flags=re.DOTALL)
    html = re.sub(r'<ul>', '', html)
    html = re.sub(r'</ul>', '', html)
    html = re.sub(r'<ol>', '', html)
    html = re.sub(r'</ol>', '', html)
    html = re.sub(r'<li>(.*?)</li>', r'• \1<br/>', html)
    html = re.sub(r'<p>(.*?)</p>', r'<para spaceAfter="10">\1</para>', html, flags=re.DOTALL)
    html = re.sub(r'<br\s*/?>', '<br/>', html)
    
    # Remove any remaining HTML tags
    html = re.sub(r'<[^>]+>', '', html)
    
    return html

@app.route('/artifact/<int:artifact_id>/export/pdf')
def export_artifact_pdf(artifact_id):
    artifact = session.query(Artifact).filter_by(id=artifact_id).first()
    if not artifact:
        abort(404)
    
    try:
        # Create PDF buffer
        buffer = io.BytesIO()
        
        # Create PDF document
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=2*cm,
            leftMargin=2*cm,
            topMargin=2*cm,
            bottomMargin=2*cm
        )
        
        # Get sample styles
        styles = getSampleStyleSheet()

        # Define custom styles
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Title'],
            fontSize=24,
            textColor=colors.HexColor('#2c3e50'),
            alignment=TA_CENTER,
            spaceAfter=30,
            fontName='Helvetica-Bold'
        )
        
        type_style = ParagraphStyle(
            'TypeBadge',
            parent=styles['Normal'],
            fontSize=12,
            textColor=colors.white,
            backColor=colors.HexColor('#3498db'),
            alignment=TA_CENTER,
            borderPadding=8,
            spaceAfter=20,
            fontName='Helvetica-Bold'
        )
        
        meta_style = ParagraphStyle(
            'MetaInfo',
            parent=styles['Normal'],
            fontSize=11,
            textColor=colors.HexColor('#666666'),
            spaceAfter=15,
            fontName='Helvetica'
        )

        content_style = ParagraphStyle(
            'ContentStyle',
            parent=styles['Normal'],
            fontSize=12,
            alignment=TA_JUSTIFY,
            spaceAfter=12,
            leading=18,
            fontName='Times-Roman'
        )
        
        heading_style = ParagraphStyle(
            'HeadingStyle',
            parent=styles['Heading2'],
            fontSize=16,
            textColor=colors.HexColor('#2c3e50'),
            spaceAfter=12,
            spaceBefore=20,
            fontName='Helvetica-Bold'
        )
        
        warning_style = ParagraphStyle(
            'WarningStyle',
            parent=styles['Normal'],
            fontSize=12,
            textColor=colors.white,
            backColor=colors.HexColor('#f39c12'),
            alignment=TA_CENTER,
            borderPadding=10,
            spaceAfter=20,
            fontName='Helvetica-Bold'
        )

        expired_style = ParagraphStyle(
            'ExpiredStyle',
            parent=styles['Normal'],
            fontSize=12,
            textColor=colors.white,
            backColor=colors.HexColor('#e74c3c'),
            alignment=TA_CENTER,
            borderPadding=10,
            spaceAfter=20,
            fontName='Helvetica-Bold'
        )
        
        # Build PDF content
        story = []
        
        # Title
        story.append(Paragraph(artifact.name, title_style))
        
        # Horizontal line after title
        story.append(HRFlowable(width="100%", thickness=2, color=colors.HexColor('#2c3e50')))
        story.append(Spacer(1, 20))

        # Type badge
        artifact_type = session.query(Type).filter_by(id=artifact.type_id).first()
        if artifact_type:
            story.append(Paragraph(f"Type: {artifact_type.name}", type_style))
        
        # Meta information table
        meta_data = []
        created_date = artifact.created_at.strftime("%B %d, %Y at %I:%M %p")
        meta_data.append(['Created:', created_date])
        
        if artifact.expiry_date:
            expiry_date = artifact.expiry_date.strftime("%B %d, %Y")
            days_remaining = (artifact.expiry_date - datetime.now().date()).days
            meta_data.append(['Expires:', expiry_date])
            meta_data.append(['Days Remaining:', str(days_remaining)])
        
        # Create meta info table
        meta_table = Table(meta_data, colWidths=[3*cm, 10*cm])
        meta_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 11),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor('#666666')),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ]))
        
        story.append(meta_table)
        story.append(Spacer(1, 20))
        
        # Expiry warning if applicable
        if artifact.expiry_date:
            days_remaining = (artifact.expiry_date - datetime.now().date()).days
            if days_remaining < 0:
                story.append(Paragraph("⚠️ THIS ARTIFACT HAS EXPIRED", expired_style))
            elif days_remaining <= 7:
                story.append(Paragraph(f"⚠️ EXPIRES IN {days_remaining} DAYS", warning_style))
        
        # Content section
        if artifact.content:
            story.append(Paragraph("Content", heading_style))
            story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#bdc3c7')))
            story.append(Spacer(1, 15))
            
            # Process content
            cleaned_content = clean_markdown_for_pdf(artifact.content)
            
            # Split into paragraphs and add to story
            paragraphs = cleaned_content.split('\n')
            for para in paragraphs:
                para = para.strip()
                if para:
                    try:
                        story.append(Paragraph(para, content_style))
                    except:
                        # Fallback for problematic content
                        story.append(Paragraph(para.encode('ascii', 'ignore').decode('ascii'), content_style))

        # Images section
        if artifact.images:
            story.append(PageBreak())
            story.append(Paragraph("Images", heading_style))
            story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#bdc3c7')))
            story.append(Spacer(1, 15))
            
            for i, image_data in enumerate(artifact.images):
                # The path is already complete from the root directory
                # Remove 'static/' prefix if it exists since we need the file system path
                image_relative_path = image_data['path']
                if image_relative_path.startswith('static/'):
                    image_relative_path = image_relative_path[7:]  # Remove 'static/' prefix
                
                # Construct the full file system path
                image_path = os.path.join(os.path.dirname(__file__), 'static', image_relative_path)
                
                try:
                    # Check if image file exists
                    if not os.path.exists(image_path):
                        error_style = ParagraphStyle(
                            'ErrorStyle',
                            parent=styles['Normal'],
                            fontSize=10,
                            textColor=colors.HexColor('#e74c3c'),
                            alignment=TA_CENTER,
                            spaceAfter=15
                        )
                        story.append(Paragraph(f"Image not found: {image_data['name']} (Path: {image_path})", error_style))
                        continue
                    
                    # Open image with PIL to get dimensions
                    with PILImage.open(image_path) as pil_img:
                        img_width, img_height = pil_img.size
                        
                        # Calculate scaling to fit page width (max 15cm)
                        max_width = 15*cm
                        max_height = 10*cm
                        
                        # Calculate aspect ratio
                        aspect_ratio = img_width / img_height

                        if img_width > img_height:
                            # Landscape orientation
                            new_width = min(max_width, img_width * 72 / 96)  # Convert pixels to points
                            new_height = new_width / aspect_ratio
                        else:
                            # Portrait orientation
                            new_height = min(max_height, img_height * 72 / 96)
                            new_width = new_height * aspect_ratio
                        
                        # Ensure image doesn't exceed page dimensions
                        if new_width > max_width:
                            new_width = max_width
                            new_height = new_width / aspect_ratio
                        if new_height > max_height:
                            new_height = max_height
                            new_width = new_height * aspect_ratio
                    
                    # Create reportlab image
                    img = RLImage(image_path, width=new_width, height=new_height)
                    
                    # Center the image
                    img.hAlign = 'CENTER'
                    
                    story.append(img)
                    
                    # Add image caption
                    caption_style = ParagraphStyle(
                        'Caption',
                        parent=styles['Normal'],
                        fontSize=10,
                        textColor=colors.HexColor('#666666'),
                        alignment=TA_CENTER,
                        spaceAfter=20,
                        fontName='Helvetica-Oblique'
                    )
                    story.append(Paragraph(f"Figure {i+1}: {image_data['name']}", caption_style))
                    
                    if i < len(artifact.images) - 1:
                        story.append(Spacer(1, 20))

                except Exception as e:
                    # If image processing fails, add a note
                    error_style = ParagraphStyle(
                        'ErrorStyle',
                        parent=styles['Normal'],
                        fontSize=10,
                        textColor=colors.HexColor('#e74c3c'),
                        alignment=TA_CENTER,
                        spaceAfter=15
                    )
                    story.append(Paragraph(f"Could not load image: {image_data['name']} - {str(e)}", error_style))
        
        # Footer information
        story.append(PageBreak())
        footer_style = ParagraphStyle(
            'FooterStyle',
            parent=styles['Normal'],
            fontSize=10,
            textColor=colors.HexColor('#666666'),
            alignment=TA_CENTER,
            spaceAfter=10
        )
        
        story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#bdc3c7')))
        story.append(Spacer(1, 20))
        story.append(Paragraph("Generated by KeepStone", footer_style))
        story.append(Paragraph(f"Export Date: {datetime.now().strftime('%B %d, %Y at %I:%M %p')}", footer_style))
        
        # Build PDF
        doc.build(story)

        # Get PDF data
        pdf_data = buffer.getvalue()
        buffer.close()
        
        # Create response
        response = make_response(pdf_data)
        response.headers['Content-Type'] = 'application/pdf'
        
        # Clean filename for download
        safe_filename = re.sub(r'[^\w\s-]', '', artifact.name.strip())
        safe_filename = re.sub(r'[-\s]+', '_', safe_filename)
        
        response.headers['Content-Disposition'] = f'attachment; filename="{safe_filename}.pdf"'
        
        return response
        
    except Exception as e:
        app.logger.error(f"PDF export error: {str(e)}")
        flash(f'Error generating PDF: {str(e)}', 'error')
        return redirect(url_for('artifact_detail', artifact_id=artifact_id))



# All routes are defined above. The following runs the app if executed directly.
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=2222, debug=True)