const express = require('express')
const bodyParser = require('body-parser')
const axios = require('axios')
const XMLHttpRequest = require("xhr2")
const cors = require('cors')
const app = express()
const router = express.Router()

app.use(bodyParser.json())
app.use(bodyParser.urlencoded({ extended: false }))
app.use(express.json())
app.use(express.urlencoded({ extended: true }))

const BASE_URL = 'http://192.168.1.80:3500';

app.get('/executeAll', async (req, res) => {
    // Get Park Ratings
    const region = req.query.region;
    console.log("getting park ratings...");
    const parkRatings = await axios.get(`${BASE_URL}/getparkrating?region=${encodeURIComponent(region)}`);

    // Select Parks Temporarily
    console.log("selecting parks...");
    const tempParks = await axios.get(`${BASE_URL}/selecttempparks`);

    // Get Review datas
    console.log("getting park reviews...");
    const parkReviews = await axios.get(`${BASE_URL}/getparkreviews`);

    // Select TOP3 Parks
    console.log("selecting TOP3 parks...");
    const top3Parks = await axios.get(`${BASE_URL}/selecttop3parks`);
    console.log('Top 3 Parks:', top3Parks.data);

    // Create WordClouds
    console.log("creating wordclouds...");
    const wc = await axios.post(`${BASE_URL}/createwc`);
    console.log('Word Clouds Created:', wc.data);

    res.json({
        parkRatings: parkRatings.data,
        tempParks: tempParks.data,
        parkReviews: parkReviews.data,
        top3Parks: top3Parks.data,
        wordClouds: wc.data
    })
})

module.exports = app;