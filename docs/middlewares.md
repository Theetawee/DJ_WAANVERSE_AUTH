Middleware

1. the dj_waanverse_auth.middleware.ClientIPMiddleware this makes the request.client_ip and request.client_ip_source available to the view
2. add it in the very first line of the middleware stack

throttles

add throttles in rest framework

1. signup-ip
2. signup-identifier
   "DEFAULT_THROTTLE_RATES": {
   "signup-ip": "2/min",
   "signup-identifier": "2/min",
   },
