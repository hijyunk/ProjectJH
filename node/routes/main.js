const express = require('express')
const bodyParser = require('body-parser')
const XMLHttpRequest = require("xhr2")
const cors = require('cors')
const app = express()
const router = express.Router()

app.use(bodyParser.json())
app.use(bodyParser.urlencoded({ extended: false }))
app.use(express.json())
app.use(express.urlencoded({ extended: true }))

app.get('/hello', (req, res) => {
    res.send("Hello World")
})

app.get('/getparkrating', async (req, res) => {
    const region = req.query.region;
    const xhr = new XMLHttpRequest();
    xhr.open("GET", `http://0.0.0.0:3500/getparkrating?region=${encodeURIComponent(region)}`);
    xhr.send();

    xhr.onload = () => {
        if (xhr.status === 200) {
            const responseData = JSON.parse(xhr.responseText);
            console.log(responseData);
            res.json(responseData);
        } else {
            console.error(xhr.status, xhr.statusText);
            res.status(500).json({error:'Failed to get park ratings'});
        }
    };
});


// app.get('/getData', (req, res) => {
//     const xhr = new XMLHttpRequest();
//     xhr.open("GET", "http://localhost:5000/users")
//     xhr.setRequestHeader("content-type", "application/json")
//     xhr.send()

//     xhr.onload = () => {
//         if (xhr.status === 200) {
//             const res = JSON.parse(xhr.response);
//             console.log(res);
//         } else {
//             console.log(xhr.statu, xhr.statusText);
//         }
//         res.send(xhr.response)
//     }
// })

// app.post('/postData', (req, res) => {
//     const xhr = new XMLHttpRequest();
//     xhr.open("POST", "http://localhost:5000/users")
//     xhr.setRequestHeader("content-type", "application/json; charset=UTF-8")
//     const data = { id:req.body.id, name:req.body.name }
//     xhr.send(JSON.stringify(data))

//     xhr.onload = () => {
//         if (xhr.status === 200) {
//             const res = JSON.parse(xhr.response);
//             console.log(res);
//         } else {
//             console.log(xhr.statu, xhr.statusText);
//         }
//         res.send(xhr.response)
//     }
// })

// app.post('/putData', (req, res) => {    // put = update 기능이다 
//     const xhr = new XMLHttpRequest();
//     xhr.open("PUT", "http://localhost:5000/users/"+req.body.id)
//     xhr.setRequestHeader("content-type", "application/json; charset=UTF-8")
//     const data = { id:req.body.id, name:req.body.name }
//     xhr.send(JSON.stringify(data))

//     xhr.onload = () => {
//         if (xhr.status === 200) {
//             const res = JSON.parse(xhr.response);
//             console.log(res);
//         } else {
//             console.log(xhr.statu, xhr.statusText);
//         }
//         res.send(xhr.response)
//     }
// })

// app.post('/deleteData', (req, res) => {    // put = update 기능이다 
//     const xhr = new XMLHttpRequest();
//     xhr.open("DELETE", "http://localhost:5000/users/"+req.body.id)  // id로 지우기 
//     xhr.setRequestHeader("content-type", "application/json; charset=UTF-8")
//     xhr.send()

//     xhr.onload = () => {
//         if (xhr.status === 200) {
//             const res = JSON.parse(xhr.response);
//             console.log(res);
//         } else {
//             console.log(xhr.statu, xhr.statusText);
//         }
//         res.send(xhr.response)
//     }
// })

module.exports = app;