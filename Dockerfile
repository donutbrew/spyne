
# Create a build argument
ARG BUILD_STAGE
ARG BUILD_STAGE=${BUILD_STAGE:-prod}

############# Build Stage: Dependencies ##################

# Start from a base image
FROM --platform=linux/amd64 ubuntu:focal as base

# Define a system argument
ARG DEBIAN_FRONTEND=noninteractive

# Install system libraries of general use
RUN apt-get update --allow-releaseinfo-change && apt-get install --no-install-recommends -y \
    build-essential \ 
    iptables \
    libdevmapper1.02.1 \
    python3.7\
    python3-pip \
    python3-setuptools \
    python3-dev \
    dpkg \
    sudo \
    wget \
    curl \
    dos2unix

############# Build Stage: Development ##################

# Build from the base image for dev
FROM base as dev

# Create working directory variable
ENV WORKDIR=/data

# Create a stage enviroment
ENV STAGE=dev

############# Build Stage: Production ##################

# Build from the base image for prod
FROM base as prod

# Create working directory variable
ENV WORKDIR=/data

# Create a stage enviroment
ENV STAGE=prod

# Copy all scripts to docker images
COPY . /SC2-spike-seq

############# Build Stage: Final ##################

# Build the final image 
FROM ${BUILD_STAGE} as final

# Set up volume directory in docker
VOLUME ${WORKDIR}

# Set up working directory in docker
WORKDIR ${WORKDIR}

# Allow permission to read and write files to current working directory
RUN chmod -R a+rwx ${WORKDIR}

############# Install java ##################

# Copy all files to docker images
COPY java /SC2-spike-seq/java

# Copy all files to docker images
COPY install_java.sh /SC2-spike-seq/install_java.sh

# Convert bash script from Windows style line endings to Unix-like control characters
RUN dos2unix /SC2-spike-seq/install_java.sh

# Allow permission to excute the bash script
RUN chmod a+x /SC2-spike-seq/install_java.sh

# Execute bash script to wget the file and tar the package
RUN bash /SC2-spike-seq/install_java.sh

############# Install bbtools ##################

# Copy all files to docker images
COPY bbtools /SC2-spike-seq/bbtools

# Copy all files to docker images
COPY install_bbtools.sh /SC2-spike-seq/install_bbtools.sh

# Convert bash script from Windows style line endings to Unix-like control characters
RUN dos2unix /SC2-spike-seq/install_bbtools.sh

# Allow permission to excute the bash script
RUN chmod a+x /SC2-spike-seq/install_bbtools.sh

# Execute bash script to wget the file and tar the package
RUN bash /SC2-spike-seq/install_bbtools.sh

############# Install Docker ##################

# Copy all files to docker images
COPY docker /SC2-spike-seq/docker

# Copy all files to docker images
COPY install_docker.sh /SC2-spike-seq/install_docker.sh

# Convert bash script from Windows style line endings to Unix-like control characters
RUN dos2unix /SC2-spike-seq/install_docker.sh

# Allow permission to excute the bash script
RUN chmod a+x /SC2-spike-seq/install_docker.sh

# Execute bash script to wget the file and tar the package
RUN bash /SC2-spike-seq/install_docker.sh

############# Install python packages ##################

# Copy all files to docker images
COPY requirements.txt /SC2-spike-seq/requirements.txt

# Install python requirements
RUN pip3 install --no-cache-dir -r /SC2-spike-seq/requirements.txt

############# Run SC2-spike-seq ##################

# Copy all files to docker images
COPY snake-kickoff /SC2-spike-seq/snake-kickoff

# Convert SC2-spike-seq from Windows style line endings to Unix-like control characters
RUN dos2unix /SC2-spike-seq/snake-kickoff

# Allow permission to excute the bash scripts
RUN chmod a+x /SC2-spike-seq/snake-kickoff

# Allow permission to read and write files to SC2-spike-seq directory
RUN chmod -R a+rwx /SC2-spike-seq

# Clean up
RUN apt-get autoremove -y && apt-get clean -y && rm -rf /var/lib/apt/lists/*

# Export bash script to path
ENV PATH "$PATH:/SC2-spike-seq"