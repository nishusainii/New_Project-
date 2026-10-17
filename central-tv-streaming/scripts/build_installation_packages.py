#!/usr/bin/env python3
"""
Automated packaging script to regenerate all 3 production zip archives
based on the latest updated codebase, bug fixes, watchdogs, and PDFs.
"""

import os
import shutil
import zipfile
import subprocess

def main():
    root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    packages_dir = os.path.join(root_dir, "production-installation-packages")
    temp_dir = os.path.join(root_dir, ".temp_packages_build")

    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir)
    os.makedirs(temp_dir, exist_ok=True)

    print("=== REBUILDING PRODUCTION INSTALLATION PACKAGES ===")
    
    # 1. Update cisai-central-tv-docker.zip
    docker_zip_path = os.path.join(packages_dir, "cisai-central-tv-docker.zip")
    docker_extract = os.path.join(temp_dir, "docker")
    print("\n[1/3] Updating cisai-central-tv-docker.zip...")
    with zipfile.ZipFile(docker_zip_path, 'r') as zip_ref:
        zip_ref.extractall(docker_extract)

    # Copy latest updated files
    shutil.copy2(os.path.join(root_dir, "server.js"), os.path.join(docker_extract, "server.js"))
    shutil.copy2(os.path.join(root_dir, "tv-detect.sh"), os.path.join(docker_extract, "tv-detect.sh"))
    shutil.copy2(os.path.join(root_dir, "management-tools", "tv-network-detector.js"), os.path.join(docker_extract, "scripts", "tv-network-detector.js"))
    
    # Copy latest public assets
    for item in ["player.html", "admin.html", "dashboard.html", "presenter.html", "login.html", "index.html"]:
        src = os.path.join(root_dir, "public", item)
        if os.path.exists(src):
            shutil.copy2(src, os.path.join(docker_extract, "public", item))

    for js_item in ["player.js", "admin.js", "presenter.js"]:
        src = os.path.join(root_dir, "public", "js", js_item)
        if os.path.exists(src):
            shutil.copy2(src, os.path.join(docker_extract, "public", "js", js_item))

    # Copy latest CSS styles
    css_src = os.path.join(root_dir, "public", "css", "style.css")
    css_dst = os.path.join(docker_extract, "public", "css")
    if os.path.exists(css_src):
        os.makedirs(css_dst, exist_ok=True)
        shutil.copy2(css_src, os.path.join(css_dst, "style.css"))

    # Copy video optimization and seamless loop scripts
    os.makedirs(os.path.join(docker_extract, "scripts"), exist_ok=True)
    for sc in ["optimize_videos_1080p.sh", "seamless-loop.js"]:
        s_src = os.path.join(root_dir, "scripts", sc)
        if os.path.exists(s_src):
            shutil.copy2(s_src, os.path.join(docker_extract, "scripts", sc))

    # Copy latest PDFs and Credentials
    arch_pdf = os.path.join(root_dir, "documentation-and-pdfs", "CiSAI_Central_TV_Streaming_Production_Architecture.pdf")
    impl_pdf = os.path.join(root_dir, "documentation-and-pdfs", "CiSAI_Central_TV_Production_Implementation_Guide.pdf")
    pi_server_pdf = os.path.join(root_dir, "documentation-and-pdfs", "Raspberry_Pi_Server_Installation_Guide.pdf")
    
    shutil.copy2(arch_pdf, os.path.join(docker_extract, "CiSAI_Central_TV_Streaming_Production_Architecture.pdf"))
    shutil.copy2(impl_pdf, os.path.join(docker_extract, "CiSAI_Central_TV_Production_Implementation_Guide.pdf"))
    if os.path.exists(pi_server_pdf):
        shutil.copy2(pi_server_pdf, os.path.join(docker_extract, "Raspberry_Pi_Server_Installation_Guide.pdf"))

    # Re-zip docker package
    os.remove(docker_zip_path)
    shutil.make_archive(docker_zip_path.replace(".zip", ""), "zip", docker_extract)
    print(f"Created {docker_zip_path} ({os.path.getsize(docker_zip_path):,} bytes)")

    # 2. Update cisai-central-tv-baremetal-vm.zip
    baremetal_zip_path = os.path.join(packages_dir, "cisai-central-tv-baremetal-vm.zip")
    baremetal_extract = os.path.join(temp_dir, "baremetal")
    print("\n[2/3] Updating cisai-central-tv-baremetal-vm.zip...")
    with zipfile.ZipFile(baremetal_zip_path, 'r') as zip_ref:
        zip_ref.extractall(baremetal_extract)

    # Copy latest updated files
    shutil.copy2(os.path.join(root_dir, "server.js"), os.path.join(baremetal_extract, "server.js"))
    shutil.copy2(os.path.join(root_dir, "tv-detect.sh"), os.path.join(baremetal_extract, "tv-detect.sh"))
    shutil.copy2(os.path.join(root_dir, "management-tools", "tv-network-detector.js"), os.path.join(baremetal_extract, "scripts", "tv-network-detector.js"))

    # Copy latest public assets
    for item in ["player.html", "admin.html", "dashboard.html", "presenter.html", "login.html", "index.html"]:
        src = os.path.join(root_dir, "public", item)
        if os.path.exists(src):
            shutil.copy2(src, os.path.join(baremetal_extract, "public", item))

    for js_item in ["player.js", "admin.js", "presenter.js"]:
        src = os.path.join(root_dir, "public", "js", js_item)
        if os.path.exists(src):
            shutil.copy2(src, os.path.join(baremetal_extract, "public", "js", js_item))

    # Copy latest CSS styles
    if os.path.exists(css_src):
        os.makedirs(os.path.join(baremetal_extract, "public", "css"), exist_ok=True)
        shutil.copy2(css_src, os.path.join(baremetal_extract, "public", "css", "style.css"))

    # Copy video optimization and seamless loop scripts
    os.makedirs(os.path.join(baremetal_extract, "scripts"), exist_ok=True)
    for sc in ["optimize_videos_1080p.sh", "seamless-loop.js"]:
        s_src = os.path.join(root_dir, "scripts", sc)
        if os.path.exists(s_src):
            shutil.copy2(s_src, os.path.join(baremetal_extract, "scripts", sc))

    # Copy latest PDFs and Credentials
    shutil.copy2(arch_pdf, os.path.join(baremetal_extract, "CiSAI_Central_TV_Streaming_Production_Architecture.pdf"))
    shutil.copy2(impl_pdf, os.path.join(baremetal_extract, "CiSAI_Central_TV_Production_Implementation_Guide.pdf"))
    if os.path.exists(pi_server_pdf):
        shutil.copy2(pi_server_pdf, os.path.join(baremetal_extract, "Raspberry_Pi_Server_Installation_Guide.pdf"))

    # Re-zip baremetal package
    os.remove(baremetal_zip_path)
    shutil.make_archive(baremetal_zip_path.replace(".zip", ""), "zip", baremetal_extract)
    print(f"Created {baremetal_zip_path} ({os.path.getsize(baremetal_zip_path):,} bytes)")

    # 3. Update cisai-central-tv-raspberry-pi.zip
    pi_zip_path = os.path.join(packages_dir, "cisai-central-tv-raspberry-pi.zip")
    pi_extract = os.path.join(temp_dir, "pi")
    print("\n[3/3] Updating cisai-central-tv-raspberry-pi.zip...")
    with zipfile.ZipFile(pi_zip_path, 'r') as zip_ref:
        zip_ref.extractall(pi_extract)

    # Copy latest scripts and tools
    shutil.copy2(os.path.join(root_dir, "tv-detect.sh"), os.path.join(pi_extract, "tv-detect.sh"))
    shutil.copy2(os.path.join(root_dir, "management-tools", "tv-network-detector.js"), os.path.join(pi_extract, "scripts", "tv-network-detector.js"))
    shutil.copy2(os.path.join(root_dir, "management-tools", "branch-relay-setup.sh"), os.path.join(pi_extract, "scripts", "branch-relay-setup.sh"))

    # Copy latest PDFs and Credentials
    shutil.copy2(arch_pdf, os.path.join(pi_extract, "CiSAI_Central_TV_Streaming_Production_Architecture.pdf"))
    shutil.copy2(impl_pdf, os.path.join(pi_extract, "CiSAI_Central_TV_Production_Implementation_Guide.pdf"))
    if os.path.exists(pi_server_pdf):
        shutil.copy2(pi_server_pdf, os.path.join(pi_extract, "Raspberry_Pi_Server_Installation_Guide.pdf"))
    if os.path.exists(os.path.join(pi_extract, "docs")):
        shutil.copy2(arch_pdf, os.path.join(pi_extract, "docs", "CiSAI_Central_TV_Streaming_Production_Architecture.pdf"))
        if os.path.exists(pi_server_pdf):
            shutil.copy2(pi_server_pdf, os.path.join(pi_extract, "docs", "Raspberry_Pi_Server_Installation_Guide.pdf"))

    # Re-zip pi package
    os.remove(pi_zip_path)
    shutil.make_archive(pi_zip_path.replace(".zip", ""), "zip", pi_extract)
    print(f"Created {pi_zip_path} ({os.path.getsize(pi_zip_path):,} bytes)")

    # Clean up temp folder
    shutil.rmtree(temp_dir)
    print("\n=== ALL 3 PRODUCTION PACKAGES SUCCESSFULLY REGENERATED ===")

if __name__ == "__main__":
    main()
