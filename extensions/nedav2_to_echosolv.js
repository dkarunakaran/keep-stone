// nedav2_to_echosolv.js
// Express router template for nedav2_to_echosolv extension

const express = require('express');
const router = express.Router();

// Example GET endpoint
router.get('/nedav2_to_echosolv', (req, res) => {
  res.json({ message: 'nedav2_to_echosolv extension is working!' });
});

// You can add POST or other endpoints here

module.exports = router;
