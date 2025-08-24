
// nedav2_to_echosolv.js
// Express router for nedav2_to_echosolv extension

const express = require('express');
const multer = require('multer');
const fs = require('fs');
const path = require('path');
const router = express.Router();
const { convertNedaV2ToHeartFailureEchoSolvInputV1, csvToJson } = require('@product/es-schema-utils');

const upload = multer({ dest: '/tmp' });

// HTML form for upload
router.get('/nedav2_to_echosolv', (req, res) => {
  res.send(`
    <html>
      <head>
        <style>body { font-family: Arial, sans-serif; margin: 2em; }</style>
      </head>
      <body>
        <form method="POST" action="/extensions/nedav2_to_echosolv" enctype="multipart/form-data">
          <label for="csvfile">Upload NEDA V2 CSV file:</label><br>
          <input type="file" name="csvfile" id="csvfile" accept=".csv" required><br><br>
          <button type="submit">Convert & Download JSON</button>
        </form>
      </body>
    </html>
  `);
});

// Handle file upload and conversion
router.post('/nedav2_to_echosolv', upload.single('csvfile'), async (req, res) => {
  if (!req.file) {
    return res.status(400).send('No file uploaded.');
  }
  try {
    console.log("nedav2_to_echosolv: Started");
    const filePath = req.file.path;
    const content = fs.readFileSync(filePath, 'utf-8');
    const data = await csvToJson(content, { noheader: false, output: 'json', trim: true });
    const converted = [];
    for (const d of data) {
      const esObj = convertNedaV2ToHeartFailureEchoSolvInputV1(d);
      converted.push(esObj);
    }
    console.log("nedav2_to_echosolv: File is converted");
    const baseName = path.basename(req.file.originalname, path.extname(req.file.originalname));
    const jsonString = JSON.stringify(converted, null, 2);
    res.setHeader('Content-Type', 'application/json');
    res.setHeader('Content-Disposition', `attachment; filename="${baseName}.json"`);
    res.send(jsonString);
    fs.unlink(filePath, () => {}); // cleanup
  } catch (err) {
    res.status(500).send(`<div style='color:red;'>Error: ${err.message}</div><a href='/extensions/nedav2_to_echosolv'>Back</a>`);
    console.error("nedav2_to_echosolv: Error", err.message);
  }
});

module.exports = router;
