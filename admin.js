const state={key:sessionStorage.getItem('venture_admin_key')||'',timer:null};
const $=s=>document.querySelector(s);
const esc=v=>String(v??'').replace(/[&<>'"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[c]));
const headers=()=>({'X-Admin-Key':state.key,'Content-Type':'application/json'});

async function api(path,options={}){
  const res=await fetch(path,{...options,headers:{...headers(),...(options.headers||{})}});
  if(!res.ok){const text=await res.text();throw new Error(text||`HTTP ${res.status}`)}
  return res.status===204?null:res.json();
}

function statCard(label,value){return `<div class="stat"><b>${value||0}</b><span>${label}</span></div>`}

async function loadStats(){
  const data=await api('/api/admin/stats');
  const s=data.by_status||{};
  $('#stats').innerHTML=statCard('Total',data.total)+statCard('New',s.New)+statCard('Contacted',s.Contacted)+statCard('Qualified',s.Qualified)+statCard('Proposal',s.Proposal)+statCard('Won',s.Won)+statCard('Lost',s.Lost);
}

function leadCard(l){
  const wa=(l.phone||'').replace(/[^0-9+]/g,'');
  const contact=[l.email,l.phone].filter(Boolean).map(esc).join(' · ');
  const emailAction=l.email?`<a href="mailto:${esc(l.email)}">Email</a>`:'';
  const whatsappAction=wa?`<a href="https://wa.me/${encodeURIComponent(wa.replace('+',''))}" target="_blank" rel="noopener">WhatsApp</a>`:'';
  const actions=[emailAction,whatsappAction].filter(Boolean).join(' · ');

  return `<article class="lead" data-id="${l.id}">
    <div>
      <h3>${esc(l.name)}</h3><small>${contact||'No contact details'}</small>
      <div class="badges"><span class="badge priority-${esc(l.priority)}">${esc(l.priority)} · ${l.score}</span><span class="badge">${esc(l.status)}</span><span class="badge">${esc(l.budget)}</span></div>
      <p><strong>Project:</strong> ${esc(l.goal)}</p>
    </div>
    <div class="lead-meta">
      <div><strong>Starting point</strong><br>${esc(l.starting_point)}</div>
      <div><strong>Source</strong><br>${esc(l.utm_source||l.source||'Direct')}</div>
      <div><strong>Received</strong><br>${new Date(l.created_at).toLocaleString()}</div>
      ${actions?`<div>${actions}</div>`:''}
    </div>
    <div class="lead-actions">
      <select class="lead-status">${['New','Contacted','Qualified','Proposal','Won','Lost'].map(s=>`<option ${s===l.status?'selected':''}>${s}</option>`).join('')}</select>
      <textarea class="lead-notes" placeholder="Private notes">${esc(l.notes||'')}</textarea>
      <button class="save" type="button">Save changes</button>
    </div>
  </article>`;
}

async function loadLeads(){
  const params=new URLSearchParams();
  const q=$('#search').value.trim();
  const status=$('#status-filter').value;
  const priority=$('#priority-filter').value;
  if(q)params.set('q',q);
  if(status)params.set('status',status);
  if(priority)params.set('priority',priority);

  const leads=await api('/api/admin/leads?'+params.toString());
  $('#leads').innerHTML=leads.length?leads.map(leadCard).join(''):'<div class="empty">No leads match these filters.</div>';
  document.querySelectorAll('.save').forEach(btn=>btn.addEventListener('click',saveLead));
}

async function saveLead(e){
  const card=e.target.closest('.lead');
  const id=card.dataset.id;
  const button=e.target;
  button.disabled=true;
  button.textContent='Saving…';

  try{
    await api(`/api/admin/leads/${id}`,{
      method:'PATCH',
      body:JSON.stringify({
        status:card.querySelector('.lead-status').value,
        notes:card.querySelector('.lead-notes').value
      })
    });
    button.textContent='Saved';
    await loadStats();
    setTimeout(()=>button.textContent='Save changes',900);
  }catch(err){
    button.textContent='Error';
    alert('Could not save this lead.');
  }finally{
    button.disabled=false;
  }
}

async function connect(){
  state.key=$('#admin-key').value.trim();
  if(!state.key)return;
  try{
    await loadStats();
    sessionStorage.setItem('venture_admin_key',state.key);
    $('#auth-box').hidden=true;
    $('#crm').hidden=false;
    await loadLeads();
  }catch(err){
    alert('Invalid admin key or server unavailable.');
  }
}

$('#connect').addEventListener('click',connect);
$('#admin-key').addEventListener('keydown',e=>{if(e.key==='Enter')connect()});
$('#refresh').addEventListener('click',()=>Promise.all([loadStats(),loadLeads()]));
['#status-filter','#priority-filter'].forEach(id=>$(id).addEventListener('change',loadLeads));
$('#search').addEventListener('input',()=>{clearTimeout(state.timer);state.timer=setTimeout(loadLeads,300)});
if(state.key){$('#admin-key').value=state.key;connect();}
