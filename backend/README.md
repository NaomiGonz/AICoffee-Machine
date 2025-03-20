# Backend
General API to accept brewing requests from web-appication, running the parameters through the machine model and then sending response back to web-appication and request to ESP32

## Instructions
Run the following command to start the backend server: 
`uvicorn main:app --reload`

Run the following command on a seperate terminal to test:
```bash
curl -X POST "http://localhost:8000/brew" \
-H "Content-Type: application/json" \
-d '{"bitterness":5, "acidity":5, "sweetness":5, "strength":5, "fruitiness":5}'
```

