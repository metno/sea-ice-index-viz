# sea-ice-index-viz
Visualization tools for the Sea Ice Indexes


**Sea Ice Extent:  Time series of Sea Ice Extent - NetCDF resource available as OpenDAP URL**

### Local deployment

To build and run locally:

* Install Docker Engine: https://docs.docker.com/engine/install/

* Install Compose plugin: https://docs.docker.com/compose/install/

* Clone this repository and build the docker container

    ```
    git clone https://github.com/metno/sea-ice-index-viz && \
    cd sea-ice-index-viz && \
    docker compose build
    ```

* Run the Docker Compose environment

    ```
    docker compose up
    ```

The bokeh-server application will be available at all of the following addresses:

```http://0.0.0.0:7000```

```http://localhost:7000```

```http://127.0.0.1:7000```

### Deployment to MET's Bokeh server

* All developments are pushed to branch `prototype`
* When the developments are good enough for a deployment 
* Massimo merges `prototype` to `main`
* Massimo updates the bokeh server (https://seaice.metsis-api.met.no/SIE). This automatically updates the cryo webpage.

*This visualization service was developed with support from Arctic Passion (European Union's Horizon 2020 research and innovation programme grant agreement No. 101003472) and the EUMETSAT Ocean and Sea Ice Satellite Application Facility (OSI SAF).*
