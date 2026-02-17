// UI-only search behavior for analysis page
function initSearch(){
    const tickers = [
        {s:'AAPL', n:'Apple Inc.'},
        {s:'TSLA', n:'Tesla, Inc.'},
        {s:'GOOGL', n:'Alphabet Inc.'},
        {s:'MSFT', n:'Microsoft Corp.'},
        {s:'BTC', n:'Bitcoin'},
        {s:'ETH', n:'Ethereum'}
    ];

    const input = document.getElementById('tickerSearch');
    const suggestions = document.getElementById('suggestions');
    const recentList = document.getElementById('recentList');
    const searchBtn = document.getElementById('searchBtn');
    let activeIndex = -1;

    if(!input) return;

    function renderSuggestions(list){
        suggestions.innerHTML = '';
        if(list.length === 0){ suggestions.hidden = true; return; }
        suggestions.hidden = false;
        list.forEach((t, i) => {
            const li = document.createElement('li');
            li.className = 'suggestion-item';
            li.tabIndex = 0;
            li.innerHTML = `<span><span class="suggestion-symbol">${t.s}</span> <span class="suggestion-name">${t.n}</span></span>`;
            li.addEventListener('click', ()=>{ input.value = t.s; suggestions.hidden = true; });
            suggestions.appendChild(li);
        });
    }

    input.addEventListener('input', ()=>{
        const q = input.value.trim().toLowerCase();
        if(q.length === 0){ suggestions.hidden = true; return; }
        const matches = tickers.filter(t => t.s.toLowerCase().includes(q) || t.n.toLowerCase().includes(q));
        renderSuggestions(matches);
        activeIndex = -1;
    });

    input.addEventListener('keydown', (e)=>{
        const items = suggestions.querySelectorAll('.suggestion-item');
        if(e.key === 'ArrowDown'){ e.preventDefault(); activeIndex = Math.min(activeIndex+1, items.length-1); }
        else if(e.key === 'ArrowUp'){ e.preventDefault(); activeIndex = Math.max(activeIndex-1, 0); }
        else if(e.key === 'Enter'){ e.preventDefault(); if(activeIndex>=0 && items[activeIndex]){ items[activeIndex].click(); } else { searchBtn.click(); } }
        items.forEach((it, idx)=> it.classList.toggle('active', idx===activeIndex));
    });

    document.addEventListener('click', (ev)=>{ if(!ev.target.closest('.search-container')) suggestions.hidden = true; });

    searchBtn && searchBtn.addEventListener('click', ()=>{
        const val = input.value.trim();
        if(!val) return;
        const li = document.createElement('li');
        li.className = 'recent-item';
        li.textContent = val.toUpperCase();
        li.addEventListener('click', ()=>{ input.value = li.textContent; });
        recentList.insertAdjacentElement('afterbegin', li);
        suggestions.hidden = true;
    });
}

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initSearch);
} else {
    initSearch();
}
