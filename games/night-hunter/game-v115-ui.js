(()=>{
'use strict';
const ending=document.getElementById('endingModal');
const fixDocumentTotal=()=>{
  const result=document.getElementById('resultNotes');
  if(!result)return;
  const value=result.textContent||'0/6';
  result.textContent=value.replace(/\/4$/,'/6');
};
if(ending)new MutationObserver(fixDocumentTotal).observe(ending,{attributes:true,attributeFilter:['class']});
fixDocumentTotal();
})();
