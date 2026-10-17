import paramiko

for ip in ['10.31.6.172', '10.31.6.173', '10.31.6.174']:
    s = paramiko.SSHClient()
    s.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    s.connect(ip, username='root', password='(cybe6@cluster)', timeout=5)
    
    stdin, stdout, stderr = s.exec_command('cat /root/output/install-cluster-exporters.sh')
    lines = stdout.read().decode().splitlines()
    
    new_lines = []
    skip = False
    for line in lines:
        if 'res=$(curl -s --connect-timeout 2' in line:
            new_lines.append(line)
            new_lines.append('        if [[ -n "$res" ]]; then')
            new_lines.append('            count=$(echo "$res" | grep -v \'#\' | grep -c . || true)')
            new_lines.append('            status="${GREEN}ONLINE${RESET}"')
            new_lines.append('        elif [[ "$port" == "9283" ]]; then')
            new_lines.append('            local http_code')
            new_lines.append('            http_code=$(curl -s -o /dev/null -w "%{http_code}" --connect-timeout 2 "http://${host}:${port}/metrics" 2>/dev/null || true)')
            new_lines.append('            if [[ "$http_code" == "200" ]]; then')
            new_lines.append('                status="${YELLOW}ONLINE (STANDBY)${RESET}"')
            new_lines.append('            fi')
            new_lines.append('        fi')
            new_lines.append('        printf "%-20s %-8s %-28b %-22s\\n" "$name" "$port" "$status" "$count metrics"')
            skip = True
        elif skip:
            if 'printf "%-24s' in line:
                skip = False
        elif 'printf "${BOLD}%-24s %-8s %-12s %-22s${RESET}\\n" "EXPORTER NAME"' in line:
            new_lines.append('    printf "${BOLD}%-20s %-8s %-18s %-22s${RESET}\\n" "EXPORTER NAME" "PORT" "STATUS" "METRICS COUNT"')
        else:
            new_lines.append(line)
            
    stdin, stdout, stderr = s.exec_command('cat > /root/output/install-cluster-exporters.sh')
    stdin.write('\n'.join(new_lines) + '\n')
    stdin.close()
    
    s.exec_command('cp /root/output/install-cluster-exporters.sh /root/exporter_install/install-cluster-exporters.sh 2>/dev/null || true')
    print(f'{ip}: Updated successfully.')
    s.close()
