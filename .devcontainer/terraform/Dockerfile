FROM debian:trixie

ARG TARGETARCH
ARG TERRAFORM_VERSION=1.13.4

RUN apt update \
    && apt install --no-install-recommends -y \
        vim git locales curl unzip ca-certificates \
    && apt clean \
    && rm -rf /var/lib/apt/lists/*

RUN localedef -f UTF-8 -i ja_JP ja_JP.utf8

# Terraform
RUN curl -Lo terraform.zip https://releases.hashicorp.com/terraform/${TERRAFORM_VERSION}/terraform_${TERRAFORM_VERSION}_linux_${TARGETARCH}.zip \
    && unzip terraform.zip -d /usr/local/bin/ \
    && rm -rf ./terraform.zip \
    && terraform -install-autocomplete

# Docker CLI
RUN curl -fsSL https://download.docker.com/linux/static/stable/$(uname -m)/docker-27.5.1.tgz \
    | tar xz --strip-components=1 -C /usr/local/bin docker/docker

# AWS CLI
RUN curl "https://awscli.amazonaws.com/awscli-exe-linux-$(uname -m).zip" -o "awscliv2.zip" \
    && unzip awscliv2.zip \
    && ./aws/install \
    && rm -rf awscliv2.zip aws

WORKDIR /workspace
