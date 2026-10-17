# syntax=docker/dockerfile:1
FROM alpine:latest

# Install Squid, Python3, and LDAP3 using host network
RUN --network=host apk add --no-cache squid python3 py3-ldap3 curl bash

# Copy custom Python LDAP auth & group helpers
COPY squid_ldap_auth.py /usr/local/bin/squid_ldap_auth.py
COPY squid_ldap_group.py /usr/local/bin/squid_ldap_group.py
RUN chmod +x /usr/local/bin/squid_ldap_auth.py /usr/local/bin/squid_ldap_group.py

# Prepare directories
RUN mkdir -p /etc/squid/acl /var/log/squid /var/spool/squid \
    && chown -R squid:squid /var/log/squid /var/spool/squid /etc/squid

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

EXPOSE 3128

ENTRYPOINT ["/entrypoint.sh"]
