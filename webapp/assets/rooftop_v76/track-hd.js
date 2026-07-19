'use strict';

let hdTrackImage=null;
const fallbackDrawBackground=drawBackground;

async function loadHdTrack(){
  try{
    const parts=await Promise.all(
      [0,1,2,3,4].map(async index=>{
        const response=await fetch(`/boss-app/assets/rooftop_v76/track_hd_${index}.b64?v=81`,{cache:'force-cache'});
        if(!response.ok)throw new Error(`Не загружена часть HD-дорожки: ${index}`);
        return (await response.text()).trim();
      })
    );

    const image=new Image();
    image.decoding='async';
    image.src=`data:image/avif;base64,${parts.join('')}`;

    if(typeof image.decode==='function')await image.decode();
    else await new Promise((resolve,reject)=>{image.onload=resolve;image.onerror=reject});

    hdTrackImage=image;
    if(!running&&typeof drawIdle==='function')drawIdle();
  }catch(error){
    console.warn('HD-дорожка не загрузилась, используется резервный фон.',error);
  }
}

loadHdTrack();

drawBackground=function drawHdBackground(t){
  if(!hdTrackImage){
    fallbackDrawBackground(t);
    return;
  }

  ctx.save();
  ctx.fillStyle='#030108';
  ctx.fillRect(0,0,W,H);

  // Ассет заранее подготовлен под пропорции игрового окна 3:4.
  // Рисуем его целиком без дополнительного приближения и размытия.
  ctx.drawImage(hdTrackImage,0,0,W,H);

  // Лёгкая коррекция контраста нужна только для читаемости игровых объектов.
  const shade=ctx.createLinearGradient(0,0,0,H);
  shade.addColorStop(0,'rgba(5,0,16,.15)');
  shade.addColorStop(.28,'rgba(8,2,18,.045)');
  shade.addColorStop(.72,'rgba(0,0,0,.015)');
  shade.addColorStop(1,'rgba(0,0,0,.13)');
  ctx.fillStyle=shade;
  ctx.fillRect(0,0,W,H);

  // Едва заметный движущийся блик оживляет статичный фон.
  const sheenX=W*(.42+.06*Math.sin(t*.00022));
  const sheen=ctx.createLinearGradient(sheenX-W*.20,H*.22,sheenX+W*.20,H);
  sheen.addColorStop(0,'rgba(132,67,255,0)');
  sheen.addColorStop(.5,'rgba(137,92,255,.045)');
  sheen.addColorStop(1,'rgba(73,225,255,0)');
  ctx.fillStyle=sheen;
  ctx.fillRect(0,H*.22,W,H*.78);

  if(typeof drawAttackTelegraph==='function')drawAttackTelegraph(t);
  if(typeof drawAtmosphere==='function')drawAtmosphere(t);
  ctx.restore();
};
