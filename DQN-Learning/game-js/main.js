//画面
const startMenu = document.getElementById('startMenu');
const main = document.getElementById('main');

//ボタンイベント
const startMenuBtn1 = document.getElementById('startMenuBtn1');
const startMenuBtn2 = document.getElementById('startMenuBtn2');
const startMenuBtn3 = document.getElementById('startMenuBtn3');
const endBtn = document.getElementById('endBtn');

startMenuBtn1.addEventListener('click', () => {
    startMenu.classList.add('is-hidden');

    setTimeout(() => {
        main.classList.remove('is-hidden');
    }, 600);
});

endBtn.addEventListener('click', () => {
    main.classList.add('is-hidden');

    setTimeout(() => {
        startMenu.classList.remove('is-hidden');
    }, 600);
});
startMenuBtn2.addEventListener('click', () => {
    // window.open('how-to-play.html', '_blank', 'width=400,height=600');
    const w = window.screen.availWidth;
    const h = window.screen.availHeight;

    window.open('etc/how-to-play.html', '_blank', `width=${w},height=${h},top=0,left=0`);
});
startMenuBtn3.addEventListener('click', () => {
    const w = window.screen.availWidth;
    const h = window.screen.availHeight;

    window.open('etc/explanation.html', '_blank', `width=${w},height=${h},top=0,left=0`);
});


// const isGravity = document.getElementById('gravity').checked ? 1 : 0;　重力


const maxSpeed = 100 / 2 + 1;
//ステータス
function getState() {

    return [
        ball.x / canvas.width,
        ball.y / canvas.height,
        // (ball.dx + 5) / 10,
        // (ball.dy + 5) / 10,
        (ball.dx * ball.speed + maxSpeed) / (maxSpeed * 2),
        (ball.dy * ball.speed + maxSpeed) / (maxSpeed * 2),
        paddle.x / (canvas.width - paddle.width),
        paddle.width / 100
        // isGravity　重力
    ];
}

// スピードボタン
const speedButtons = document.querySelectorAll('.speed-btn-border');
const speedDisplay = document.getElementById('speedDisplay');

const speeds = [1, 2, 5, 10, 100];

speedButtons.forEach((btn, index) => {
    btn.addEventListener('click', () => {
        curentTimeScale = speeds[index];

        speedDisplay.textContent = (curentTimeScale * 100) + "%";

        console.log(`速度を${curentTimeScale}倍に変更`);
    });
});

// ニューロンモニター
// 中間層
const nCanvasH = document.getElementById('neuronCanvasHidden');
const nCtxH = nCanvasH.getContext('2d');

const neuronColsH = 8;
const neuronRowsH = 16;

nCanvasH.width = nCanvasH.clientWidth;//htmlのcanvasの大きさに設定する
nCanvasH.height = nCanvasH.clientHeight;//htmlのcanvasの大きさに設定する

const cellW = nCanvasH.width / neuronColsH;//マスの大きさ
const cellH = nCanvasH.height / neuronRowsH;//マスの大きさ

function drawHiddenNeurons(activations) {

    nCtxH.clearRect(0, 0, nCanvasH.width, nCanvasH.height);

    activations.forEach((val, i) => {
        const x = (i % neuronColsH) * cellW + cellW / 2;//グリッド作成　x0~7にグリッド1マス分掛けてから中心を指定
        const y = Math.floor(i / neuronColsH) * cellH + cellH / 2;//y0~15にグリッド1マス分掛けてから中心を指定

        // valの値から色を決めて付ける
        const alpha = Math.max(0.1, val);//最低でも色を付けるために0.1
        nCtxH.beginPath();
        nCtxH.arc(x, y, Math.min(cellW, cellH) / 3, 0, Math.PI * 2);//xyマスの中心座標,半径はマスの1/3,0度~360度で丸を描く
        nCtxH.fillStyle = `rgba(127, 255, 212, ${alpha})`;//色の透明度をalphaで指定

        if (val > 0.5) {
            nCtxH.shadowBlur = 10;//ぼかしの長さ
            nCtxH.shadowColor = "aquamarine";//ぼかしの色
        } else {
            nCtxH.shadowBlur = 0;
        }
        nCtxH.fill();
    });
}

// 出力層
const nCanvasO = document.getElementById('neuronCanvasOutput');
const nCtxO = nCanvasO.getContext('2d');

nCanvasO.width = nCanvasO.clientWidth;
nCanvasO.height = nCanvasO.clientHeight;

const neuronBar = ['LEFT', 'STAY', 'RIGHT'];
const neuronBarW = nCanvasO.width / 4;

const neuronLeftValue = document.getElementById('neuronLeftValue');
const neuronStayValue = document.getElementById('neuronStayValue');
const neuronRightValue = document.getElementById('neuronRightValue');

function drawOutputNeurons(qValues) {
    nCtxO.clearRect(0, 0, nCanvasO.width, nCanvasO.height);

    neuronLeftValue.textContent = qValues[0].toFixed(2); 
    neuronStayValue.textContent = qValues[1].toFixed(2);
    neuronRightValue.textContent = qValues[2].toFixed(2);

    const maxQ = Math.max(...qValues);//一番高いQ値
    const minQ = Math.min(...qValues);//一番低いQ値

    const range = Math.max(0.1, maxQ - minQ);//最大値と最小値の幅 0除算対策で最低でも0.1にする

    qValues.forEach((val, i) => {
        const ratio = (val - minQ) / range;//(今の値-最小値)/全体幅 最小値を0, 最大値を1
        const barHeight = (0.05 + ratio * 0.9) * (nCanvasO.height * 0.8);//棒の最大の長さをcanvasの80％

        x = i * (nCanvasO.width / 3) + (nCanvasO.width / 3 - neuronBarW) * 0.5;//棒の位置

        nCtxO.fillStyle = (val === maxQ && val > 0) ? '#bbf5ff' : 'rgba(79, 172, 254, 0.5)';//一番高いQ値だったら色を変える

        nCtxO.shadowBlur = ratio * 15;//自信があるほど光らせる
        nCtxO.shadowColor = '#4facfe';

        nCtxO.fillRect(x, nCanvasO.height, neuronBarW, -barHeight);
    });
}



let curentTimeScale = 1;

async function gameStep() {
    for (let n = 0; n < curentTimeScale; n++) {
        const gamma = persoonality.gamma;//現在のガンマ取得
        const learningRate = persoonality.learningRate;//現在の学習率取得

        const currentState = getState();//状況A
        const action = decideAction(currentState);//行動を選択
        const result = updateGame(action);//選んだ行動を実行
        const nextState = getState();//状況B

        memory.push({//記録セットをリプレイバッファにpush
            state: currentState,//状況A
            action: action,//行動
            reward: result.reward,//報酬
            nextState: nextState,//状況B
            done: result.done//ゲームが終わったかどうか
        });

        await train(gamma, learningRate);

        updateTargetModel();

        if (result.done) break;
    }
    
    draw();

    if (play) {
        requestAnimationFrame(gameStep);
    }
}

// メニューボタン
const startBtn = document.getElementById('startBtn');
const stopBtn = document.getElementById('stopBtn');

let play = false;

// スタートボタン
startBtn.addEventListener('click', () => {
    if (play) {
        return;
    } else {
        play = true;
        gameStep();
    }
});
// 停止ボタン
stopBtn.addEventListener('click', () => {
    play = false;
});

// データ管理ボタン
const dataControlBtn = document.getElementById('dataControlBtn');
const closeBtn = document.getElementById('closeBtn');

const dataMenu = document.getElementById('dataMenu');
const overlay = document.getElementById('overlay');

const toggleDataMenu = () => {
    dataMenu.classList.toggle('data-active');
    overlay.classList.toggle('data-active');
}
// メニュー開く
dataControlBtn.addEventListener('click', toggleDataMenu);
// メニュー閉じる
[closeBtn, overlay].forEach(el => {
    el.addEventListener('click', (e) => {
        if (e.target === el) toggleDataMenu();
    })
})

// データメニュー
const saveBtn = document.getElementById('saveBtn');
const loadBtn = document.getElementById('loadBtn');
const importBtn = document.getElementById('importBtn');
const exportBtn = document.getElementById('exportBtn');
const nnResetBtn = document.getElementById('nnResetBtn');

// セーブ
async function saveModel() {
    await model.save('localstorage://breakout-model');
    toggleDataMenu();
    hopUpWindow("セーブしました");
}
// ロード
async function loadModel() {
    const wasPlaying = play;
    play = false;
    model = await tf.loadLayersModel('localstorage://breakout-model');
    updateTargetModel();
    toggleDataMenu();
    hopUpWindow("ロードしました");
    play = wasPlaying;
    if(play) gameStep();
}
// インポート
importBtn.addEventListener('change', async (e) => {
    const files = e.target.files;
    if(files.length < 2) {
        toggleDataMenu();
        hopUpWindow("jsonとbinの2つのファイルをドラッグとかctrlで複数選択してね");
        return;
    }

    const selectedFiles = Array.from(files);

    const jsonFile = selectedFiles.find(f => f.name.endsWith('.json'));
    const weightsFile = selectedFiles.find(f => f.name.endsWith('.bin'));

    if (!jsonFile || !weightsFile) {
        return hopUpWindow("ファイルが正しくないです");
    }

    try {
        model = await tf.loadLayersModel(tf.io.browserFiles([jsonFile, weightsFile]));

        visuaalizationModel = tf.model({
            inputs: model.inputs,
            outputs: model.layers[1].output
        });

        updateTargetModel();
        toggleDataMenu();
        hopUpWindow("インポートしました");
    } catch (err) {
        console.error(err);
        hopUpWindow("インポート失敗...ファイル壊れてるかも");
    }
});

// エクスポート
exportBtn.addEventListener('click', async () => {
    await model.save('downloads://breakout-model');
    toggleDataMenu();
    hopUpWindow("エクスポートしました");
});

// リセット
nnResetBtn.addEventListener('click', async () => {
    if(!confirm("ニューラルネットワークをリセットしますか？")) return;

    play = false;
    await initModel();
    toggleDataMenu();
    hopUpWindow("リセットしました");
});

// ホップアップ表示
const hopUp = document.getElementById('hopUp');
function hopUpWindow(val) {
    hopUp.textContent = val;
    hopUp.classList.add('data-active');
    setTimeout(() => {
        hopUp.classList.remove('data-active');
    }, 2000);
}
// ボタンを押したら
saveBtn.addEventListener('click', saveModel);
loadBtn.addEventListener('click', loadModel);


gameStep();