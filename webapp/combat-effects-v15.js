(()=>{
  'use strict';
  const classByAction={hit:'fx-hit',defend:'fx-defend',heal:'fx-heal'};
  const duration={hit:440,defend:680,heal:760};

  function replay(button, className, ms){
    button.classList.remove(className);
    void button.offsetWidth;
    button.classList.add(className);
    window.setTimeout(()=>button.classList.remove(className),ms);
  }

  document.addEventListener('click',event=>{
    const button=event.target.closest('.combat [data-action]');
    if(!button||button.disabled)return;
    const action=button.dataset.action;
    const className=classByAction[action];
    if(!className)return;
    replay(button,className,duration[action]);

    if(action==='defend'){
      const shield=document.querySelector('.fx-shield');
      if(shield){shield.classList.remove('play');void shield.offsetWidth;shield.classList.add('play');}
    }
    if(action==='heal'){
      const heal=document.querySelector('.fx-heal');
      if(heal){heal.classList.remove('play');void heal.offsetWidth;heal.classList.add('play');}
    }
  },true);
})();
