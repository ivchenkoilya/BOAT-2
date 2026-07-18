(()=>{
  'use strict';

  const stage=document.getElementById('bossStage');
  if(!stage||stage.querySelector('.boss-swipe-v23'))return;

  const surface=document.createElement('div');
  surface.className='boss-swipe-v23';
  surface.setAttribute('aria-hidden','true');
  stage.appendChild(surface);

  let gesture=null;
  let velocity=0;
  let lastTime=0;
  let momentumFrame=0;

  const cancelMomentum=()=>{
    if(momentumFrame)cancelAnimationFrame(momentumFrame);
    momentumFrame=0;
  };

  const scrollByPixels=delta=>{
    window.scrollBy(0,delta);
    const root=document.scrollingElement||document.documentElement||document.body;
    if(root&&Math.abs(delta)>0&&window.scrollY===0)root.scrollTop+=delta;
  };

  surface.addEventListener('touchstart',event=>{
    if(event.touches.length!==1)return;
    cancelMomentum();
    const touch=event.touches[0];
    gesture={x:touch.clientX,y:touch.clientY,vertical:null};
    velocity=0;
    lastTime=performance.now();
  },{passive:true});

  surface.addEventListener('touchmove',event=>{
    if(!gesture||event.touches.length!==1)return;
    const touch=event.touches[0];
    const dx=touch.clientX-gesture.x;
    const dy=touch.clientY-gesture.y;

    if(gesture.vertical===null){
      if(Math.abs(dx)<3&&Math.abs(dy)<3)return;
      gesture.vertical=Math.abs(dy)>=Math.abs(dx)*.8;
    }
    if(!gesture.vertical)return;

    const now=performance.now();
    const elapsed=Math.max(8,now-lastTime);
    const scrollDelta=-dy;
    scrollByPixels(scrollDelta);
    velocity=scrollDelta/elapsed*16;
    gesture.x=touch.clientX;
    gesture.y=touch.clientY;
    lastTime=now;
    event.preventDefault();
    event.stopPropagation();
  },{passive:false});

  const finish=()=>{
    if(!gesture)return;
    const startVelocity=velocity;
    gesture=null;
    if(Math.abs(startVelocity)<1.2)return;
    let current=startVelocity;
    const momentum=()=>{
      current*=.91;
      if(Math.abs(current)<.35){momentumFrame=0;return;}
      scrollByPixels(current);
      momentumFrame=requestAnimationFrame(momentum);
    };
    momentumFrame=requestAnimationFrame(momentum);
  };

  surface.addEventListener('touchend',finish,{passive:true});
  surface.addEventListener('touchcancel',()=>{gesture=null;cancelMomentum()},{passive:true});
})();
