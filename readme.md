# KeepStone

A modern, responsive web application for storing artifacts related to token and expiry dates, troubleshooting info, and other information. Built with Flask, SQLAlchemy, and SQLite with a beautiful Bootstrap UI.

## Features

- ✅ **Add/Update/Delete Artifacts**: Easily manage your artifacts with name, usage description, and expiry date
- ✅ **Expiry Tracking**: Visual indicators for active, expiring soon, and expired artifacts
- ✅ **Search Functionality**: Find artifacts by name or usage description
- ✅ **Responsive UI**: Modern, mobile-friendly interface with gradient backgrounds and animations
- ✅ **SQLite Database**: Persistent storage using SQLAlchemy ORM
- ✅ **Docker Support**: Containerized deployment with Docker and docker-compose

## Installation

### Prerequisites
- Docker and Docker Compose installed

### Run with Docker Compose

1. Clone or create the project files
2. Change directory to the cloned repo
3. Start the application:
```bash
docker-compose up --build -d
```
4. Open your browser and navigate to `http://localhost:2222`
5. Stop the application
```bash
docker-compose down
```

## Usage

### Adding Artifacts
1. Click "Add New Artifact" button
2. Fill in:
   - **Artifact Name**: Descriptive name (e.g., "GitHub API artifact")
   - **Used For**: Purpose description (e.g., "Accessing private repositories")
   - **Expiry Date**: When the artifact expires
3. Click "Add artifact"

### Managing Artifacts
- **View All Artifacts**: The dashboard shows all artifacts with status indicators
- **Search**: Use the search box to find specific artifacts
- **Delete**: Click the trash icon to remove a artifact
- **Update**: Click the edit icon to update a artifact
- **Status Indicators**:
  - 🟢 **Green**: Active (more than 14 days remaining)
  - 🟡 **Yellow**: Expires Soon (14 days or less)
  - 🔴 **Red**: Expired

### Artifact Status

The application automatically categorizes artifacts:
- **Active**: More than 14 days until expiry
- **Expires Soon**: 14 days or less until expiry  
- **Expired**: Past the expiry date

## Database

The application uses SQLite by default, with the database file stored in `/app/instance/data.db` inside the container. This is mounted as a Docker volume for persistence.

### Database Schema

```sql
artifacts (
    id INTEGER PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    used_for VARCHAR(200) NOT NULL,
    expiry_date DATE NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
)
```


## Support

For issues and questions:
1. Check the logs: `docker-compose logs keep-stone`
2. Ensure all required files are in place
3. Verify Docker and docker-compose are properly installed
