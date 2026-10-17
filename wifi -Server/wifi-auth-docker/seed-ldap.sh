#!/usr/bin/env bash
set -e

GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}Waiting for OpenLDAP server to become ready on 127.0.0.1:389 (dc=innspark,dc=in)...${NC}"
until docker exec wifi-openldap ldapsearch -x -H ldap://127.0.0.1 -D "cn=admin,dc=innspark,dc=in" -w "AdminPassword123!" -b "dc=innspark,dc=in" >/dev/null 2>&1; do
    sleep 1
done

echo -e "${GREEN}OpenLDAP is ready!${NC}"

# Check if users already exist
if docker exec wifi-openldap ldapsearch -x -H ldap://127.0.0.1 -D "cn=admin,dc=innspark,dc=in" -w "AdminPassword123!" -b "ou=Users,dc=innspark,dc=in" "(uid=john.doe)" dn 2>/dev/null | grep -q "dn: uid=john.doe"; then
    echo -e "${GREEN}LDAP already seeded with Innspark Wi-Fi users.${NC}"
else
    echo -e "${BLUE}Seeding Wi-Fi users and groups into LDAP...${NC}"
    docker exec -i wifi-openldap ldapadd -c -x -H ldap://127.0.0.1 -D "cn=admin,dc=innspark,dc=in" -w "AdminPassword123!" < ldap/users.ldif || true
    echo -e "${GREEN}Seeding completed successfully!${NC}"
fi
