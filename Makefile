all:
	(cd python && uvicorn app:app --host 0.0.0.0 --port 3500 --reload) &
temp:
	(cd node && nodemon app.js) &
stop-uvicorn:
	pkill uvicorn
stop-node:
	pkill -f "nodemon"