const state = { data: null, roadmap: null, milestone: 'P1', filter: 'All', outcome: 'All', sort: 'newest', query: '', layout: 'timeline', view: 'timeline' };
const featured = new Set(['EV-0027','EV-0032','EV-0054','EV-0063','EV-0064']);
const chapters = [
 {id:'EV-0027',theme:'sage',number:'01',title:'First, prove the fold.',note:'The original LeHome environment establishes a working control.'},
 {id:'EV-0054',theme:'gray',number:'02',title:'A false positive changes the plan.',note:'A completed script was not a credible fold. Return to physical evidence.'},
 {id:'EV-0064',theme:'sand',number:'03',title:'Same policy. Different reach.',note:'The XLeRobot layout changes contact geometry and camera views.'}
];
const list = document.querySelector('#experiment-list');
const dialog = document.querySelector('#detail-dialog');
const formatDate = (date) => new Intl.DateTimeFormat('en', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' }).format(new Date(date));
const formatBytes = (bytes) => `${(bytes / 1024 / 1024).toFixed(bytes > 1024 ** 3 ? 0 : 1)} MB`;
const escapeHtml = (text) => text.replace(/[&<>'"]/g, (c) => ({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[c]));

function render() {
  const roadmapView = state.view === 'roadmap';
  document.querySelector('.toolbar').hidden = roadmapView;
  document.querySelector('#chapters').hidden = roadmapView || state.view === 'archive';
  document.querySelector('#roadmap').hidden = !roadmapView;
  document.querySelector('.workspace').hidden = roadmapView;
  if (roadmapView) { renderRoadmap(); return; }
  const query = state.query.toLowerCase();
  const items = state.data.experiments.filter((item) => {
    const matchesFilter = state.filter === 'All' || state.filter === item.phase || state.filter.toLowerCase() === item.status;
    const haystack = `${item.id} ${item.experiment} ${item.hypothesis} ${item.learning}`.toLowerCase();
    const matchesView = state.view === 'archive' || featured.has(item.id);
    return matchesFilter && matchesView && (state.outcome === 'All' || state.outcome === item.status) && haystack.includes(query);
  });
  if (state.sort === 'oldest') items.reverse();
  document.querySelector('#view-count').textContent = `${items.length} experiments in view`;
  document.querySelector('#chapters').hidden = state.view === 'archive';
  list.className = `experiment-list ${state.layout}`;
  list.innerHTML = items.length && state.layout !== 'grid' ? `<div class="table-scroll"><table><thead><tr><th>Experiment</th><th>Phase</th><th>Hypothesis / question</th><th>Outcome</th><th>Evidence</th><th>Recorded</th><th></th></tr></thead><tbody>${items.map(item => `<tr class="experiment-row ${item.status}" data-id="${item.id}"><td><div class="experiment-name"><img src="${item.thumbnail}" alt="" loading="lazy"><span>${escapeHtml(item.experiment)}<small>${item.id}</small></span></div></td><td><span class="phase">${item.phase}</span></td><td class="question-cell" title="${escapeHtml(item.hypothesis)}">${escapeHtml(item.hypothesis)}</td><td><span class="status"><i></i>${item.status}</span></td><td><button class="evidence-button" aria-label="Watch ${item.id}">▷ &nbsp; Watch film</button></td><td class="recorded">${formatDate(item.recordedAt)}</td><td><button class="row-open" aria-label="Open ${item.id}">↗</button></td></tr>`).join('')}</tbody></table></div>` : items.length ? items.map((item) => `
    <article class="experiment-row ${item.status}" data-id="${item.id}">
      <time class="date">${formatDate(item.recordedAt).replace(', ', '<br>')}</time><i class="node"></i>
      <div class="experiment-card" tabindex="0">
        <div class="thumb"><img src="${item.thumbnail}" alt="Frame from ${escapeHtml(item.experiment)}" loading="lazy" onerror="this.remove()"><span class="play">▶</span></div>
        <div class="card-copy"><div class="card-top"><span class="id">${item.id}</span><span class="phase">${item.phase}</span><span class="status">${item.status}</span></div><h3>${escapeHtml(item.hypothesis)}</h3><p>${escapeHtml(item.learning)}</p></div>
        <div class="artifact-meta"><span><strong>${item.artifacts.length}</strong> camera ${item.artifacts.length === 1 ? 'view' : 'views'}<br>${formatBytes(item.artifacts.reduce((s,a)=>s+a.bytes,0))}</span><button>Open evidence →</button></div>
      </div>
    </article>`).join('') : '<div class="empty">No experiments match this view.</div>';
  list.querySelectorAll('.experiment-row').forEach((row) => row.addEventListener('click', () => openExperiment(row.dataset.id)));
}

function openExperiment(id) {
  const item = state.data.experiments.find((entry) => entry.id === id);
  if (!item) return;
  const hasThree = ['top','left','right'].every(view=>item.artifacts.some(a=>a.view===view));
  const film = hasThree ? '/combined/'+item.id+'.mp4' : (item.artifacts.find(a=>/folding|highlight/.test(a.view)) || item.artifacts[0]).url;
  const content = document.querySelector('#dialog-content');
  content.innerHTML = `<div class="dialog-layout"><div class="dialog-media"><video controls playsinline preload="auto" poster="${item.thumbnail}" src="${film}"></video><p class="playback-status" role="status"></p><button class="retry-play" type="button">Play video</button></div><div class="dialog-info"><p class="eyebrow">${item.id} · ${item.phase} · ${formatDate(item.recordedAt)}</p><h2>${escapeHtml(item.hypothesis)}</h2><div class="insight"><span>Why we tried it</span><p>${escapeHtml(item.hypothesis)} This experiment isolates one uncertainty in the learning system.</p></div><div class="insight"><span>What we learned</span><p>${escapeHtml(item.learning)}</p></div><div class="insight"><span>Outcome</span><p class="${item.status}">${item.status.toUpperCase()} · ${item.artifacts.length} retained artifact${item.artifacts.length === 1 ? '' : 's'}</p></div><p class="film-caption">${hasThree?'Overhead · left wrist · right wrist. One combined recording, aligned at the first frame.':'Experiment recording'}</p></div></div>`;
  const video = content.querySelector('video');
  const associations = state.roadmap?.milestones.filter(m => m.evidence.includes(id)) ?? [];
  const links = document.createElement('div');
  links.className = 'milestone-links';
  links.innerHTML = associations.map(m => '<button type="button" data-milestone="' + m.id + '">' + m.id + ' · ' + escapeHtml(m.title) + ' →</button>').join('');
  links.querySelectorAll('button').forEach(button => button.addEventListener('click', () => {
    dialog.close();
    state.milestone = button.dataset.milestone;
    document.querySelector('[data-view="roadmap"]').click();
  }));
  content.querySelector('.dialog-info').append(links);
  const status = content.querySelector('.playback-status');
  const startPlayback = () => {
    status.textContent = 'Loading video…';
    video.play().catch(error => {status.textContent = error.name === 'NotAllowedError' ? 'Press Play video to start.' : 'Unable to play this recording. Try another camera.';});
  };
  video.addEventListener('playing',()=>{status.textContent='';content.querySelector('.retry-play').hidden=true;});
  video.addEventListener('error',()=>{status.textContent='This recording could not be decoded. Try another camera.';content.querySelector('.retry-play').hidden=false;});
  video.addEventListener('pause',()=>{content.querySelector('.retry-play').hidden=false;});
  content.querySelector('.retry-play').addEventListener('click',startPlayback);
  content.querySelectorAll('.artifact-tabs button').forEach((button) => button.addEventListener('click', () => {
    video.src = button.dataset.url;
    startPlayback();
    content.querySelectorAll('.artifact-tabs button').forEach((b) => b.classList.toggle('active', b === button));
  }));
  dialog.showModal();
  startPlayback();
}

async function init() {
  state.data = await fetch('/experiments.json').then((res) => res.json());
  try {
    const response = await fetch('/roadmap.json');
    if (!response.ok) throw new Error('Roadmap unavailable');
    state.roadmap = await response.json();
    state.milestone = state.roadmap.milestones.find(m => m.status === 'current')?.id ?? state.roadmap.milestones[0]?.id;
    const sidebar = document.querySelector('#roadmap-links');
    sidebar.innerHTML = state.roadmap.milestones.slice(0, 3).map(m => '<button data-milestone="' + m.id + '"><i class="' + (m.status === 'proved' ? 'done' : m.status === 'current' ? 'current' : '') + '"></i>' + escapeHtml(m.title) + '</button>').join('');
    sidebar.querySelectorAll('button').forEach(button => button.addEventListener('click', () => {
      state.milestone = button.dataset.milestone;
      document.querySelector('[data-view="roadmap"]').click();
    }));
  } catch (error) { state.roadmapError = 'Milestones could not be loaded. Restart Fold Lab with npm run dev and refresh.'; }
  document.querySelector('#experiment-count').textContent = state.data.summary.experiments;
  document.querySelector('#artifact-count').textContent = state.data.summary.artifacts;
  document.querySelector('#archive-size').textContent = `${(state.data.summary.bytes / 1024 ** 3).toFixed(2)} GB archive`;
  document.querySelector('#sync-label').textContent = `Synced ${new Date(state.data.generatedAt).toLocaleTimeString([], {hour:'2-digit', minute:'2-digit'})}`;
  document.querySelector('#chapters').innerHTML = chapters.map(c=>`<button class="chapter ${c.theme}" data-chapter="${c.id}"><span class="paper back"></span><span class="paper front"></span><span class="grain"></span><span class="chapter-number">FIELD NOTES / ${c.number}</span><strong>${c.title}</strong><span class="chapter-note">${c.note}</span><span class="chapter-link">Watch chapter ↗</span></button>`).join('');
  document.querySelectorAll('[data-chapter]').forEach(b=>b.addEventListener('click',()=>openExperiment(b.dataset.chapter)));
  render();
}

const roadmapSection = document.createElement('section');
roadmapSection.id = 'roadmap';
roadmapSection.hidden = true;
roadmapSection.setAttribute('aria-label', 'Milestone roadmap');
document.querySelector('.workspace').before(roadmapSection);
document.querySelector('nav').insertAdjacentHTML('afterbegin', '<button class="nav-item" data-view="roadmap"><span>◎</span>Roadmap</button>');
document.querySelector('.tabs').insertAdjacentHTML('afterbegin', '<button data-tab="roadmap">Roadmap</button>');
const researchList = document.querySelector('.milestone-list');
researchList.id = 'roadmap-links';
researchList.innerHTML = '';
const obsolete = document.querySelector('.milestone-list.muted');
obsolete?.previousElementSibling?.remove();
obsolete?.remove();

function renderRoadmap() {
  const container = document.querySelector('#roadmap');
  if (!state.roadmap) { container.innerHTML = '<p class="empty" role="alert">' + escapeHtml(state.roadmapError || 'Loading milestones…') + '</p>'; return; }
  const milestones = state.roadmap.milestones;
  const selected = milestones.find(m => m.id === state.milestone) ?? milestones[0];
  if (!selected) { container.innerHTML = '<p class="empty">No milestones defined.</p>'; return; }
  const proved = milestones.filter(m => m.status === 'proved').length;
  document.querySelector('#view-count').textContent = proved + ' / ' + milestones.length + ' milestones proved';
  const related = selected.evidence.map(id => ({ id, item: state.data.experiments.find(e => e.id === id) }));
  container.innerHTML = '<div class="roadmap-heading"><p class="eyebrow">FROM BASELINE TO DEPLOYMENT</p><h2>A folding robot, one proven step at a time.</h2><p>Milestone status is reviewed explicitly. Linked experiments include failed and inconclusive attempts.</p></div>' +
    '<div class="roadmap-layout"><div class="roadmap-steps" role="group" aria-label="Choose a milestone">' +
    milestones.map(m => '<button class="roadmap-step ' + m.status + (m.id === selected.id ? ' selected' : '') + '" aria-pressed="' + (m.id === selected.id) + '" data-select-milestone="' + m.id + '"><span class="roadmap-id">' + m.id + '</span><span><strong>' + escapeHtml(m.title) + '</strong><small>' + m.criteria.filter(c => c.done).length + '/' + m.criteria.length + ' criteria reviewed · ' + m.status + '</small></span></button>').join('') +
    '</div><article class="milestone-detail"><p class="eyebrow">' + selected.id + ' · ' + selected.status.toUpperCase() + '</p><h2>' + escapeHtml(selected.title) + '</h2><p>' + escapeHtml(selected.goal) + '</p>' +
    '<div class="milestone-next"><strong>Next action</strong><p>' + escapeHtml(selected.next) + '</p></div><h3>Blocker / constraint</h3><p>' + escapeHtml(selected.blocker) + '</p><h3>Acceptance criteria</h3><ul class="criteria">' +
    selected.criteria.map(c => '<li><span class="criterion-mark ' + (c.done ? 'checked' : '') + '" aria-label="' + (c.done ? 'Reviewed' : 'Pending') + '">' + (c.done ? '✓' : '○') + '</span>' + escapeHtml(c.text) + '</li>').join('') +
    '</ul><h3>Experiment evidence</h3><div class="milestone-evidence">' +
    (related.length ? related.map(({id,item}) => item ? '<button data-watch="' + id + '"><img src="' + item.thumbnail + '" alt=""><span><strong>' + id + ' · ' + escapeHtml(item.hypothesis) + '</strong><small>' + item.status.toUpperCase() + ' · ' + escapeHtml(item.learning) + '</small></span><span aria-hidden="true">↗</span></button>' : '<p>' + id + ' — not yet available in the catalog</p>').join('') : '<p class="no-evidence">No recorded evidence linked yet. This milestone has not been demonstrated.</p>') +
    '</div><p class="roadmap-source">Source: docs/mvp-milestones.md · Edit Markdown and refresh. Evidence links do not check off criteria automatically.</p></article></div>';
  container.querySelectorAll('[data-select-milestone]').forEach(button => button.addEventListener('click', () => { state.milestone = button.dataset.selectMilestone; renderRoadmap(); }));
  container.querySelectorAll('[data-watch]').forEach(button => button.addEventListener('click', () => openExperiment(button.dataset.watch)));
}

document.querySelector('#search').addEventListener('input', (event) => { state.query = event.target.value; render(); });
document.querySelector('#search-button').addEventListener('click', () => {
  if (state.view === 'roadmap') document.querySelector('[data-view="timeline"]').click();
  document.querySelector('#search').focus();
});
document.querySelector('#latest-button').addEventListener('click', () => openExperiment(state.data.experiments[0].id));
document.querySelectorAll('[data-layout]').forEach((button) => button.addEventListener('click', () => { state.layout = button.dataset.layout; document.querySelectorAll('[data-layout]').forEach((b)=>b.classList.toggle('active',b===button)); render(); }));
document.querySelectorAll('[data-jump]').forEach((button) => button.addEventListener('click', () => openExperiment(button.dataset.jump)));
document.querySelectorAll('.nav-item,[data-tab]').forEach((button) => button.addEventListener('click', () => {
  state.view = button.dataset.view || button.dataset.tab;
  state.layout = state.view === 'evidence' ? 'grid' : 'timeline';
  const titles = {
    roadmap: ['Milestone roadmap', 'The next action and the evidence required to advance.'],
    archive: ['Diagnostic archive', 'Setup probes and intermediate attempts.'],
    timeline: ['Experiment timeline', 'Every attempt, the reason behind it, and what changed next.'],
    hypotheses: ['Hypothesis progression', 'The decisive questions that changed the direction of the work.'],
    evidence: ['Evidence library', 'Every retained recording, grouped by experiment and ready to watch.'],
  };
  document.querySelector('#view-title').textContent = titles[state.view][0];
  document.querySelector('#view-subtitle').textContent = titles[state.view][1];
  document.querySelectorAll('.nav-item,[data-tab]').forEach((item) => item.classList.toggle('active', (item.dataset.view || item.dataset.tab) === state.view));
  document.querySelectorAll('[data-layout]').forEach((item) => item.classList.toggle('active', item.dataset.layout === state.layout));
  render();
}));
document.querySelector('#phase').addEventListener('change', e => {state.filter=e.target.value;render();});
document.querySelector('#outcome').addEventListener('change', e => {state.outcome=e.target.value;render();});
document.querySelector('#sort').addEventListener('change', e => {state.sort=e.target.value;render();});
document.querySelectorAll('[data-filter-link]').forEach(button=>button.addEventListener('click',()=>{state.filter=button.dataset.filterLink;document.querySelector('#phase').value=state.filter;document.querySelector('[data-tab="archive"]').click();}));
dialog.addEventListener('close',()=>{const video=dialog.querySelector('video');if(video)video.pause();});
document.querySelector('.dialog-close').addEventListener('click', () => dialog.close());
dialog.addEventListener('click', (event) => { if (event.target === dialog) dialog.close(); });
init();
