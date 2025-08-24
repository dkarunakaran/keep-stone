// Extension: CSV to JSON
const express = require('express');
const multer = require('multer');
const csv = require('csvtojson');
const path = require('path');
const fs = require('fs');

const router = express.Router();
const upload = multer({ dest: '/tmp' });

// Display a simple HTML form for CSV upload
router.get('/csv_to_json', (req, res) => {
  res.send(`
    <html>
      <head>
        <style>
          body { font-family: Arial, sans-serif; margin: 2em; }
          .result { margin-top: 1em; }
        </style>
      </head>
      <body>
        <form method="POST" action="/extensions/csv_to_json" enctype="multipart/form-data">
          <label for="csvfile">Upload CSV file:</label><br>
          <input type="file" name="csvfile" id="csvfile" accept=".csv" required><br><br>
          <button type="submit">Convert to JSON & Download</button>
        </form>
      </body>
    </html>
  `);
});

// Handle CSV file upload and conversion
router.post('/csv_to_json', upload.single('csvfile'), async (req, res) => {
  if (!req.file) {
    return res.status(400).send('No file uploaded.');
  }
  try {
    console.error("csv_to_json: Started");
    const filePath = req.file.path;
    const originalName = req.file.originalname || 'output.csv';
    const baseName = path.basename(originalName, path.extname(originalName));
    const jsonArray = await csv().fromFile(filePath);
    fs.unlinkSync(filePath); // Clean up temp file
    const jsonString = JSON.stringify(jsonArray, null, 2);
    console.error("csv_to_json: File is converted");
    res.setHeader('Content-Type', 'application/json');
    res.setHeader('Content-Disposition', `attachment; filename="${baseName}.json"`);
    res.send(jsonString);
  } catch (err) {
    res.status(400).send(`<div style='color:red;'>Error: ${err.message}</div><a href='/extensions/csv-to-json'>Back</a>`);
    console.error("csv_to_json: Error", err.message);
  }
});

module.exports = router;
