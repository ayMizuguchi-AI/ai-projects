// スピードボタン
const speedButtons = document.querySelectorAll('.speed-btn-border');
const speedDisplay = document.getElementById('speedDisplay');

const speeds = [1, 2, 5, 10, 100];

speedButtons.forEach((btn, index) => {
    btn.addEventListener('click', () => {
        curentTimeScale = speeds[index];
        speedDisplay.textContent = (curentTimeScale * 100) + "%";
    });
});


const epsilonRange = document.getElementById('epsilonRange');

epsilonRange.addEventListener('input', (e) => {//Rangeを動かしたら
    epsilon = parseFloat(e.target.value) / 100;//eはイベントでeの中のtarget(スライダー)の中のvalue(値)
    epsilonRange.style.setProperty('--pos', `${epsilon * 100}%`);
    epsilonPercent.textContent = `${Math.round(epsilon * 100)}%`;
});

// テキストアニメーション
const chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ@#$%&*';
const container = document.getElementById('textContainer');
let currentId = 0;

async function renderText(targetText) {
    const myId = ++currentId;

    const formattedText = targetText.replace(/\\n/g, '\n');//改行

    container.classList.add('is-processing');

    container.textContent = '';

    for (let i = 0; i < formattedText.length; i++) {
        if (myId !== currentId) return;

        let currentDisplay = container.textContent;

        for (let j = 0; j < 3; j++) {
            const randomChar = chars[Math.floor(Math.random() * chars.length)];
            container.textContent = currentDisplay + randomChar;
            await new Promise(r => setTimeout(r, 20));

            if(myId !== currentId) return;
        }

        container.textContent = currentDisplay + formattedText[i];
    }

    if (myId === currentId) {
        container.classList.remove('is-processing');
    }
}

document.querySelectorAll('.highlight').forEach(e => {
    e.addEventListener('mouseenter', () => {
        const text = e.getAttribute('data-text');
        renderText(text);
    });
    e.addEventListener('mouseleave', () => {
        currentId++;
        container.textContent = '';
    });
});