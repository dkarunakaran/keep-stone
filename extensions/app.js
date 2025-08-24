// Simple Node.js app with extension routing
const express = require('express');
const bodyParser = require('body-parser');

const app = express();
const PORT = process.env.PORT || 3333;

app.use(bodyParser.json({ limit: '2mb' }));

// Mount extension routes
const csvToJson = require('./csv_to_json');
app.use('/extensions', csvToJson);

const nedav2ToEchosolv = require('./nedav2_to_echosolv');
app.use('/extensions', nedav2ToEchosolv);

app.get('/', (req, res) => {
  res.send('Hello from Node.js container!');
});

app.listen(PORT, () => {
  console.log(`Node.js app running on port ${PORT}`);
});
