#!/bin/sh
if [ -z "${PREFIX}" ]; then
    PREFIX_PARAM="";
else
    PREFIX_PARAM="--prefix ${PREFIX}";
fi

bokeh serve --port ${PORT} --address 0.0.0.0 --allow-websocket-origin ${ORIGIN} ${PREFIX_PARAM} --log-level ${BOKEH_LOG_LEVEL} /SIE