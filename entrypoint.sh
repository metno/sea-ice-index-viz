#!/bin/bash
panel serve --port ${PORT} --address 0.0.0.0 --log-level ${LOG_LEVEL} /bokeh-app/daily /bokeh-app/monthly
