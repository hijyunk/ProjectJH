const express = require('express')
const morgan = require('morgan')
const path = require('path')
const app = express()
const bodyParser = require('body-parser')
const cookieParser = require('cookie-parser')
const axios = require('axios')
const cors = require('cors')
const XMLHttpRequest = require("xhr2")

app.set('port', 8500)
app.use(morgan('dev'))
app.use(bodyParser.json())
app.use(bodyParser.urlencoded({ extended: false }))
app.use(cookieParser())
app.use(express.static(path.join(__dirname, 'public')))
app.use(cors());

var main = require('./routes/main.js')
app.use('/', main)

app.listen(app.get('port'), () => {
    console.log("8500 Port: Sever Started~!!")
});
