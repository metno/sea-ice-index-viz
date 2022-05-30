# sea-ice-index-viz
Visualization tools for the Sea Ice Indexes


**Sea Ice Extent:  Time series of Sea Ice Extent - NetCDF resource available as OpenDAP URL**

### Demo

* **Notebook:**
    
   https://mybinder.org/v2/gh/metno/sea-ice-index-viz/main?labpath=bokeh-app%2FSIE.ipynb


* **Bokeh APP:**

   https://mybinder.org/v2/gh/metno/sea-ice-index-viz/main?urlpath=/proxy/5006/bokeh-app    


### Local deployment

To build and run locally:

* Install Docker

    For installing Docker CE, follow the [official instructions](https://docs.docker.com/engine/install/).
    
        e.g.: Docker-CE on Ubuntu can be setup using Docker’s official convenience script:

        ```
        curl https://get.docker.com | sh \
        && sudo systemctl --now enable docker
        ```


* Install `docker-compose`

    ```
    apt install python3-pip && pip3 install docker-compose
    ``` 

* Clone this repository and build the docker container
    
    ```
    git clone https://github.com/metno/sea-ice-index-viz && \
    cd WUI && \
    docker-compose build
    ```

* Run the docker-compose environment
    
    ```
    docker-compose up
    ```

The bokeh-server application will be availavble at:

```http://0.0.0.0:7000/SIE```