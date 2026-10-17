FROM freeradius/freeradius-server:latest

# Copy customized configurations
COPY clients.conf /etc/freeradius/clients.conf
COPY mods-available/ldap /etc/freeradius/mods-available/ldap

# Enable the LDAP module by symlinking
RUN ln -sf /etc/freeradius/mods-available/ldap /etc/freeradius/mods-enabled/ldap \
    && chown -R freerad:freerad /etc/freeradius

# Switch to non-root freerad user
USER freerad

EXPOSE 1812/udp 1813/udp

# Run in debug foreground mode to output live auth logs to docker compose
CMD ["freeradius", "-X"]
