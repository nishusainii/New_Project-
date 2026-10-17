import os
import glob
import zipfile
import shutil

slides_dir = "/home/nishusaini/Desktop/Innspark/Palo Alto Firewall /Palo Alto Training/extracted_slides"
images = sorted(glob.glob(os.path.join(slides_dir, "*.jpg")))

pptx_path = "/home/nishusaini/Desktop/Innspark/Palo Alto Firewall /Palo Alto Training/Palo_Alto_Complete_Training_Slides.pptx"
temp_dir = "/tmp/pptx_build"

if os.path.exists(temp_dir):
    shutil.rmtree(temp_dir)

os.makedirs(os.path.join(temp_dir, "_rels"), exist_ok=True)
os.makedirs(os.path.join(temp_dir, "docProps"), exist_ok=True)
os.makedirs(os.path.join(temp_dir, "ppt", "_rels"), exist_ok=True)
os.makedirs(os.path.join(temp_dir, "ppt", "slides", "_rels"), exist_ok=True)
os.makedirs(os.path.join(temp_dir, "ppt", "slideLayouts", "_rels"), exist_ok=True)
os.makedirs(os.path.join(temp_dir, "ppt", "slideMasters", "_rels"), exist_ok=True)
os.makedirs(os.path.join(temp_dir, "ppt", "media"), exist_ok=True)
os.makedirs(os.path.join(temp_dir, "ppt", "theme"), exist_ok=True)

# 1. Copy images
media_files = []
for idx, img in enumerate(images, start=1):
    dest_name = f"image{idx}.jpg"
    shutil.copyfile(img, os.path.join(temp_dir, "ppt", "media", dest_name))
    media_files.append((idx, dest_name, img))

num_slides = len(media_files)

# 2. [Content_Types].xml
content_types = ['<?xml version="1.0" encoding="UTF-8" standalone="yes"?>',
'<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">',
'<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>',
'<Default Extension="xml" ContentType="application/xml"/>',
'<Default Extension="jpg" ContentType="image/jpeg"/>',
'<Override PartName="/ppt/presentation.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.presentation.main+xml"/>',
'<Override PartName="/ppt/slideMasters/slideMaster1.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slideMaster+xml"/>',
'<Override PartName="/ppt/slideLayouts/slideLayout1.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slideLayout+xml"/>',
'<Override PartName="/ppt/theme/theme1.xml" ContentType="application/vnd.openxmlformats-officedocument.theme+xml"/>',
'<Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>',
'<Override PartName="/docProps/app.xml" ContentType="application/vnd.openxmlformats-officedocument.extended-properties+xml"/>']

for i in range(1, num_slides + 1):
    content_types.append(f'<Override PartName="/ppt/slides/slide{i}.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slide+xml"/>')

content_types.append('</Types>')

with open(os.path.join(temp_dir, "[Content_Types].xml"), "w") as f:
    f.write("\n".join(content_types))

# 3. _rels/.rels
with open(os.path.join(temp_dir, "_rels", ".rels"), "w") as f:
    f.write("""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="ppt/presentation.xml"/>
<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/>
<Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/extended-properties" Target="docProps/app.xml"/>
</Relationships>""")

# 4. docProps/core.xml & app.xml
with open(os.path.join(temp_dir, "docProps", "core.xml"), "w") as f:
    f.write("""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:dcterms="http://purl.org/dc/terms/" xmlns:dcmitype="http://purl.org/dc/dcmitype/" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
<dc:title>Palo Alto Networks 11+ Hours Video Training Slides</dc:title>
<dc:creator>Nishu Saini</dc:creator>
</cp:coreProperties>""")

with open(os.path.join(temp_dir, "docProps", "app.xml"), "w") as f:
    f.write(f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties" xmlns:vt="http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes">
<TotalTime>0</TotalTime>
<Words>0</Words>
<Application>Microsoft Macintosh PowerPoint</Application>
<PresentationFormat>On-screen Show (16:9)</PresentationFormat>
<Paragraphs>0</Paragraphs>
<Slides>{num_slides}</Slides>
<Notes>0</Notes>
<HiddenSlides>0</HiddenSlides>
<MMClips>0</MMClips>
<ScaleCrop>false</ScaleCrop>
<HeadingPairs><vt:vector size="2" baseType="variant"><vt:variant><vt:lpstr>Theme</vt:lpstr></vt:variant><vt:variant><vt:i4>1</vt:i4></vt:variant></vt:vector></HeadingPairs>
<TitlesOfParts><vt:vector size="1" baseType="lpstr"><vt:lpstr>Office Theme</vt:lpstr></vt:vector></TitlesOfParts>
<Company>Innspark Solutions</Company>
<LinksUpToDate>false</LinksUpToDate>
<SharedDoc>false</SharedDoc>
<HyperlinksChanged>false</HyperlinksChanged>
<AppVersion>16.0000</AppVersion>
</Properties>""")

# 5. ppt/presentation.xml
pres_slides = []
for i in range(1, num_slides + 1):
    pres_slides.append(f'<p:sldId id="{255 + i}" r:id="rId{i+1}"/>')

with open(os.path.join(temp_dir, "ppt", "presentation.xml"), "w") as f:
    f.write(f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<p:presentation xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">
<p:sldMasterIdLst><p:sldMasterId id="2147483648" r:id="rId1"/></p:sldMasterIdLst>
<p:sldIdLst>
{"".join(pres_slides)}
</p:sldIdLst>
<p:sldSz cx="12192000" cy="6858000" type="screen16x9"/>
<p:notesSz cx="6858000" cy="9144000"/>
</p:presentation>""")

# 6. ppt/_rels/presentation.xml.rels
pres_rels = ['<?xml version="1.0" encoding="UTF-8" standalone="yes"?>',
'<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">',
'<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideMaster" Target="slideMasters/slideMaster1.xml"/>']

for i in range(1, num_slides + 1):
    pres_rels.append(f'<Relationship Id="rId{i+1}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slide" Target="slides/slide{i}.xml"/>')

pres_rels.append('</Relationships>')
with open(os.path.join(temp_dir, "ppt", "_rels", "presentation.xml.rels"), "w") as f:
    f.write("\n".join(pres_rels))

# 7. ppt/theme/theme1.xml
with open(os.path.join(temp_dir, "ppt", "theme", "theme1.xml"), "w") as f:
    f.write("""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<a:theme xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" name="Office Theme">
<a:themeElements>
<a:clrScheme name="Office">
<a:dk1><a:sysClr val="windowText" lastClr="000000"/></a:dk1>
<a:lt1><a:sysClr val="window" lastClr="FFFFFF"/></a:lt1>
<a:dk2><a:srgbClr val="1F497D"/></a:dk2>
<a:lt2><a:srgbClr val="EEECE1"/></a:lt2>
<a:accent1><a:srgbClr val="FA582D"/></a:accent1>
<a:accent2><a:srgbClr val="0F2942"/></a:accent2>
<a:accent3><a:srgbClr val="9BBB59"/></a:accent3>
<a:accent4><a:srgbClr val="8064A2"/></a:accent4>
<a:accent5><a:srgbClr val="4BACC6"/></a:accent5>
<a:accent6><a:srgbClr val="F79646"/></a:accent6>
<a:hlink><a:srgbClr val="0000FF"/></a:hlink>
<a:folHlink><a:srgbClr val="800080"/></a:folHlink>
</a:clrScheme>
<a:fontScheme name="Office">
<a:majorFont><a:latin typeface="Calibri"/></a:majorFont>
<a:minorFont><a:latin typeface="Calibri"/></a:minorFont>
</a:fontScheme>
<a:fmtScheme name="Office">
<a:fillStyleLst><a:solidFill><a:schemeClr val="phClr"/></a:solidFill></a:fillStyleLst>
<a:lnStyleLst><a:ln w="9525"><a:solidFill><a:schemeClr val="phClr"/></a:solidFill></a:ln></a:lnStyleLst>
<a:effectStyleLst><a:effectLst/></a:effectStyleLst>
<a:bgFillStyleLst><a:solidFill><a:schemeClr val="phClr"/></a:solidFill></a:bgFillStyleLst>
</a:fmtScheme>
</a:themeElements>
</a:theme>""")

# 8. ppt/slideMasters/slideMaster1.xml & _rels
with open(os.path.join(temp_dir, "ppt", "slideMasters", "slideMaster1.xml"), "w") as f:
    f.write("""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<p:sldMaster xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">
<p:cSld><p:spTree><p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr><p:grpSpPr/></p:spTree></p:cSld>
<p:clrMap bg1="lt1" tx1="dk1" bg2="lt2" tx2="dk2" accent1="accent1" accent2="accent2" accent3="accent3" accent4="accent4" accent5="accent5" accent6="accent6" hlink="hlink" folHlink="folHlink"/>
<p:sldLayoutIdLst><p:sldLayoutId id="2147483649" r:id="rId1"/></p:sldLayoutIdLst>
</p:sldMaster>""")

with open(os.path.join(temp_dir, "ppt", "slideMasters", "_rels", "slideMaster1.xml.rels"), "w") as f:
    f.write("""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideLayout" Target="../slideLayouts/slideLayout1.xml"/>
<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/theme" Target="../theme/theme1.xml"/>
</Relationships>""")

# 9. ppt/slideLayouts/slideLayout1.xml & _rels
with open(os.path.join(temp_dir, "ppt", "slideLayouts", "slideLayout1.xml"), "w") as f:
    f.write("""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<p:sldLayout xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main" type="blank">
<p:cSld name="Blank"><p:spTree><p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr><p:grpSpPr/></p:spTree></p:cSld>
<p:clrMapOvr><a:masterClrMapping/></p:clrMapOvr>
</p:sldLayout>""")

with open(os.path.join(temp_dir, "ppt", "slideLayouts", "_rels", "slideLayout1.xml.rels"), "w") as f:
    f.write("""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideMaster" Target="../slideMasters/slideMaster1.xml"/>
</Relationships>""")

# 10. Generate slides (slide1.xml to slideN.xml)
for i in range(1, num_slides + 1):
    img_rel_id = "rId2"
    
    # 16:9 canvas is 12192000 x 6858000 EMU
    # Centered image: 11500000 x 6468750 EMU, offset x=346000, y=194625
    slide_xml = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<p:sld xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">
<p:cSld>
<p:spTree>
<p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr>
<p:grpSpPr/>
<p:pic>
<p:nvPicPr>
<p:cNvPr id="{i+1}" name="SlideImage{i}"/>
<p:cNvPicPr><a:picLocks noChangeAspect="1"/></p:cNvPicPr>
<p:nvPr/>
</p:nvPicPr>
<p:blipFill>
<a:blip r:embed="rId2"/>
<a:stretch><a:fillRect/></a:stretch>
</p:blipFill>
<p:spPr>
<a:xfrm>
<a:off x="346000" y="194625"/>
<a:ext cx="11500000" cy="6468750"/>
</a:xfrm>
<a:prstGeom prst="rect"><a:avLst/></a:prstGeom>
</p:spPr>
</p:pic>
</p:spTree>
</p:cSld>
<p:clrMapOvr><a:masterClrMapping/></p:clrMapOvr>
</p:sld>"""
    
    with open(os.path.join(temp_dir, "ppt", "slides", f"slide{i}.xml"), "w") as f:
        f.write(slide_xml)
        
    slide_rel = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideLayout" Target="../slideLayouts/slideLayout1.xml"/>
<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image" Target="../media/image{i}.jpg"/>
</Relationships>"""
    with open(os.path.join(temp_dir, "ppt", "slides", "_rels", f"slide{i}.xml.rels"), "w") as f:
        f.write(slide_rel)

# 11. Zip into .pptx
with zipfile.ZipFile(pptx_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
    for root, dirs, files in os.walk(temp_dir):
        for file in files:
            full_path = os.path.join(root, file)
            rel_path = os.path.relpath(full_path, temp_dir)
            zipf.write(full_path, rel_path)

print(f"Successfully generated Native PowerPoint Presentation (.pptx): {pptx_path}")

# Copy to Desktop root
desktop_pptx = "/home/nishusaini/Desktop/Innspark/Palo_Alto_Complete_Training_Slides.pptx"
shutil.copyfile(pptx_path, desktop_pptx)
print(f"Copied to: {desktop_pptx}")
