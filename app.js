const intakeForm=document.querySelector('form[name="project-intake"]');
const startingPoint=document.getElementById('starting-point');
const langToggle=document.getElementById('lang-toggle');
let currentLang='ar';

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

function prepareIntakeDefaults(){
  if(!intakeForm)return;
  const defaults={
    country:'Not provided',
    background:'Not provided',
    available_time:'Not decided yet',
    timeline:'Later / exploring',
    model:'',
    risk_preference:''
  };
  Object.entries(defaults).forEach(([name,value])=>upsertHidden(name,value));
}

function captureAttribution(){
  const params=new URLSearchParams(window.location.search);
  ['utm_source','utm_medium','utm_campaign'].forEach(key=>upsertHidden(key,params.get(key)||''));
  upsertHidden('referrer',document.referrer||'direct');
  upsertHidden('source',params.get('utm_source')||document.referrer||'direct');
}

function applyLanguage(lang){
  currentLang=lang;
  document.documentElement.lang=lang;
  document.documentElement.dir=lang==='ar'?'rtl':'ltr';

  document.querySelectorAll('[data-en]').forEach(element=>{
    if(!element.dataset.arHtml)element.dataset.arHtml=element.innerHTML;
    element.innerHTML=lang==='en'?element.dataset.en:element.dataset.arHtml;
  });

  document.querySelectorAll('[data-en-placeholder]').forEach(element=>{
    if(!element.dataset.arPlaceholder)element.dataset.arPlaceholder=element.getAttribute('placeholder')||'';
    element.setAttribute('placeholder',lang==='en'?element.dataset.enPlaceholder:element.dataset.arPlaceholder);
  });

  if(langToggle)langToggle.textContent=lang==='ar'?'English':'العربية';
  document.title=lang==='ar'
    ?'Digital Venture Studio — مشاريع رقمية، تطبيقات، منصات وذكاء اصطناعي'
    :'Digital Venture Studio — Ideas, Products, AI & Automation';
}

if(langToggle){
  langToggle.addEventListener('click',()=>applyLanguage(currentLang==='ar'?'en':'ar'));
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
  prepareIntakeDefaults();
  captureAttribution();

  intakeForm.addEventListener('submit',async event=>{
    event.preventDefault();
    const button=intakeForm.querySelector('button[type="submit"]');
    const original=button.innerHTML;
    button.disabled=true;
    button.textContent=currentLang==='ar'?'جارٍ الإرسال…':'Submitting…';

    const form=new FormData(intakeForm);
    const keys=['name','phone','country','starting_point','background','available_time','budget','timeline','model','risk_preference','goal','source','utm_source','utm_medium','utm_campaign','referrer'];
    const payload={};
    keys.forEach(key=>payload[key]=form.get(key)||null);
    payload.email=`lead-${Date.now()}@example.com`;

    try{
      const response=await fetch('/api/leads',{
        method:'POST',
        headers:{'Content-Type':'application/json'},
        body:JSON.stringify(payload)
      });
      if(!response.ok)throw new Error(await response.text());
      window.location.assign('/thanks.html');
    }catch(error){
      console.error(error);
      button.disabled=false;
      button.innerHTML=original;
      alert(currentLang==='ar'
        ?'تعذر إرسال الطلب. تأكد من البيانات وحاول مرة أخرى.'
        :'Your request could not be submitted. Please check your details and try again.');
    }
  });
}

applyLanguage('ar');
