#!/bin/bash
GROUP=4
if [ "$GROUP" -eq 0 ]; then
    echo "Error: please update your group number!"
    exit 1  
fi
HOST=$(oc get route acmeair-main-route -n group-${GROUP} --template='{{ .spec.host }}')
PORT=80

LOAD_LEVEL=$1

case $LOAD_LEVEL in
  "low")
    THREAD=10
    USER=100
    DURATION=60
    RAMP=60
    DELAY=30
    ;;
  "medium")
    THREAD=300
    USER=3500
    DURATION=60
    RAMP=15
    DELAY=2
    ;;
  "high")
    THREAD=600
    USER=8000
    DURATION=120
    RAMP=10
    DELAY=1
    ;;
  *)
    echo "Error: Please specify a valid load level (low, medium, high)."
    exit 1
    ;;
esac

echo HOST=${HOST}
echo PORT=${PORT}
echo THREAD=${THREAD}
echo USER=${USER}
echo DURATION=${DURATION}
echo RAMP=${RAMP}
echo DELAY=${DELAY}

curl http://${HOST}/booking/loader/load
echo ""
curl http://${HOST}/flight/loader/load
echo ""
curl http://${HOST}/customer/loader/load?numCustomers=10000
echo ""

jmeter -n -t acmeair-jmeter/scripts/AcmeAir-microservices-mpJwt.jmx \
 -DusePureIDs=true \
 -JHOST=${HOST} \
 -JPORT=${PORT} \
 -JTHREAD=${THREAD} \
 -JUSER=${USER} \
 -JDURATION=${DURATION} \
 -JRAMP=${RAMP} \
 -JDELAY=${DELAY}
