const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');

function getIndividualVideos(mediaDir) {
  if (!fs.existsSync(mediaDir)) return [];
  const files = fs.readdirSync(mediaDir);
  return files
    .filter(f => !f.startsWith('.') && f !== 'seamless_master_loop.mp4' && f.endsWith('.mp4'))
    .sort();
}

function computeVideoDuration(filePath) {
  try {
    const cmd = `ffprobe -v error -show_entries format=duration -of json "${filePath}"`;
    const out = execSync(cmd, { encoding: 'utf8', timeout: 10000 });
    const parsed = JSON.parse(out);
    return parseFloat(parsed?.format?.duration) || 0;
  } catch (e) {
    console.error(`[SeamlessLoop] Error probing duration for ${filePath}:`, e.message);
    return 0;
  }
}

function buildSeamlessMasterLoop(mediaDir, dataDir) {
  const videos = getIndividualVideos(mediaDir);
  const targetFile = path.join(mediaDir, 'seamless_master_loop.mp4');
  const chaptersFile = path.join(dataDir, 'seamless_chapters.json');

  if (videos.length === 0) {
    if (fs.existsSync(targetFile)) fs.unlinkSync(targetFile);
    if (fs.existsSync(chaptersFile)) fs.unlinkSync(chaptersFile);
    return null;
  }

  // Calculate chapters
  let offset = 0.0;
  const chapters = [];
  for (let i = 0; i < videos.length; i++) {
    const fn = videos[i];
    const fullPath = path.join(mediaDir, fn);
    const dur = computeVideoDuration(fullPath);
    const start = Math.round(offset * 1000) / 1000;
    const end = Math.round((offset + dur) * 1000) / 1000;
    chapters.push({
      index: i,
      filename: fn,
      displayName: fn.replace(/^\d+_/, '').replace(/\.mp4$/i, '').replace(/_/g, ' '),
      startTime: start,
      endTime: end,
      duration: Math.round(dur * 1000) / 1000
    });
    offset += dur;
  }

  const totalDuration = Math.round(offset * 1000) / 1000;

  // Build ffmpeg concat list
  const listFile = path.join(mediaDir, '.concat_list.tmp');
  const fileLines = videos.map(v => `file '${path.resolve(mediaDir, v)}'`).join('\n');
  fs.writeFileSync(listFile, fileLines, 'utf8');

  try {
    console.log(`[SeamlessLoop] Concatenating ${videos.length} video(s) into seamless master loop...`);
    const tempTarget = path.join(mediaDir, 'seamless_master_loop.tmp.mp4');
    execSync(
      `ffmpeg -y -f concat -safe 0 -i "${listFile}" -c copy -movflags +faststart "${tempTarget}"`,
      { stdio: 'pipe', timeout: 60000 }
    );
    if (fs.existsSync(listFile)) fs.unlinkSync(listFile);
    fs.renameSync(tempTarget, targetFile);
    fs.chmodSync(targetFile, 0o664);

    const chapterData = {
      enabled: true,
      url: '/media/seamless_master_loop.mp4',
      totalDuration,
      files: videos,
      chapters
    };

    if (!fs.existsSync(dataDir)) fs.mkdirSync(dataDir, { recursive: true });
    fs.writeFileSync(chaptersFile, JSON.stringify(chapterData, null, 2), 'utf8');
    console.log(`[SeamlessLoop] Successfully generated ${targetFile} (${totalDuration}s)`);
    return chapterData;
  } catch (err) {
    if (fs.existsSync(listFile)) fs.unlinkSync(listFile);
    console.error('[SeamlessLoop] Concat error:', err.message);
    return null;
  }
}

function getSeamlessMetadata(mediaDir, dataDir) {
  const chaptersFile = path.join(dataDir, 'seamless_chapters.json');
  const targetFile = path.join(mediaDir, 'seamless_master_loop.mp4');
  const currentVideos = getIndividualVideos(mediaDir);

  if (currentVideos.length === 0) return null;

  if (fs.existsSync(chaptersFile) && fs.existsSync(targetFile)) {
    try {
      const cached = JSON.parse(fs.readFileSync(chaptersFile, 'utf8'));
      // Check if file list matches
      const cachedFiles = cached.files || [];
      if (
        cachedFiles.length === currentVideos.length &&
        cachedFiles.every((f, i) => f === currentVideos[i])
      ) {
        return cached;
      }
    } catch (e) {
      // Fall through to rebuild
    }
  }

  // Need to build or rebuild
  return buildSeamlessMasterLoop(mediaDir, dataDir);
}

module.exports = {
  buildSeamlessMasterLoop,
  getSeamlessMetadata,
  getIndividualVideos
};
