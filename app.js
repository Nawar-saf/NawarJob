const intakeForm=document.querySelector('form[name="project-intake"]');
const startingPoint=document.getElementById('starting-point');

function upsertHidden(name,value){
  if(!intakeForm)return;
  let input=intakeForm.querySelector(`input[name="${name}"]`);
  if(!input){
    input=document.createElement('input');
    input.type='hidden';
    input.name=name;
    intakeForm.appendChild(input);
  }
  input.value=value||'';
}

function captureAttribution(){
  const params=new URLSearchParams(window.location.search);
  ['utm_source','utm_medium','utm_campaign','utm_content','utm_term'].forEach(key=>upsertHidden(key,params.get(key)||''));
  upsertHidden('referrer',document.referrer||'direct');
  upsertHidden('landing_page',window.location.pathname);
  upsertHidden('submitted_at',new Date().toISOString());
}

function calculateLeadScore(formData){
  let score=0;
  const budget=formData.get('budget')||'';
  const timeline=formData.get('timeline')||'';
  const starting=formData.get('starting_point')||'';
  const time=formData.get('available_time')||'';

  if(budget.includes('$150,000+'))score+=5;
  else if(budget.includes('$50,000–$150,000'))score+=4;
  else if(budget.includes('$10,000–$50,000'))score+=3;
  else if(budget.includes('$2,000–$10,000'))score+=2;
  else if(budget.includes('Under $2,000'))score+=1;

  if(timeline==='Immediately')score+=4;
  else if(timeline==='Within 30 days')score+=3;
  else if(timeline==='Within 3 months')score+=2;
  else if(timeline==='Within 6 months')score+=1;

  if(starting==='I already have an idea'||starting==='I want to grow an existing business')score+=2;
  if(starting==='I have capital and want an opportunity')score+=2;
  if(time==='Full-time'||time==='I want an operator or team to run it')score+=1;

  let priority='Low';
  if(score>=10)priority='High';
  else if(score>=6)priority='Medium';

  return {score,priority};
}

document.querySelectorAll('[data-path]').forEach(link=>{
  link.addEventListener('click',()=>{
    if(startingPoint){
      startingPoint.value=link.dataset.path;
      startingPoint.dispatchEvent(new Event('change',{bubbles:true}));
    }
  });
});

if(intakeForm){
  captureAttribution();
  intakeForm.addEventListener('submit',()=>{
    const formData=new FormData(intakeForm);
    const result=calculateLeadScore(formData);
    upsertHidden('lead_score',String(result.score));
    upsertHidden('lead_priority',result.priority);
    upsertHidden('submitted_at',new Date().toISOString());
  });
}
