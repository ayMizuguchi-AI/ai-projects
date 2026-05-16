//報酬
const rewardUpdateBtn = document.getElementById('rewardUpdateBtn');
const rewardResetBtn = document.getElementById('rewardResetBtn');
let rewardState = {
    time: 0,//時間経過
    drop: -2,//落下
    break: 1,//破壊
    hit: 0.5,//打返
    all: 5//全消
};
function rewardUpdate() {
    rewardState.time = document.getElementById('rewardInput1').value;
    rewardState.drop = document.getElementById('rewardInput2').value;
    rewardState.break = document.getElementById('rewardInput3').value;
    rewardState.hit = document.getElementById('rewardInput4').value;
    rewardState.all = document.getElementById('rewardInput5').value;
}
rewardUpdateBtn.addEventListener('click', () => {
    rewardUpdate();
})
rewardResetBtn.addEventListener('click', () => {
    setTimeout(() => {
        rewardUpdate();
    }, 0);
})

const canvas = document.getElementById('gameCanvas');
const ctx = canvas.getContext('2d');

//ボール
let ball = {
    x: 0,
    y: 0,
    dx: 1,
    dy: -1,
    speed: 5,
    radius: 5
};
// バー
let paddle = {
    x: 150,
    width: 80,
    height: 8,
    speed: 8
};
// ブロック
const blocks = [];
const blockRowCount = 4;
const blockColumnCount = 6;
const blockPadding = 5;
const blockW = 50;
const blockH = 20;

const blockColumnCountHalf = Math.floor(blockColumnCount / 2);
const blockOffsetTop = 10;
let blockOffsetLeft = 0;


if (blockColumnCount % 2 === 0) {
    blockOffsetLeft = canvas.width / 2 - (blockPadding / 2 + blockColumnCountHalf * blockW + (blockColumnCountHalf - 1) * blockPadding);
} else {
    blockOffsetLeft = canvas.width / 2 - (blockColumnCountHalf * blockW + blockW / 2 + blockColumnCountHalf * blockPadding);
}

function initBlocks() {
    for (let c = 0; c < blockColumnCount; c++) {
        blocks[c] = [];
        for (let r = 0; r < blockRowCount; r++) {
            blocks[c][r] = {
                x: c * (blockW + blockPadding) + blockOffsetLeft,
                y: r * (blockH + blockPadding) + blockOffsetTop,
                status: 1
            };
        }
    }
}


// ゲーム初期化
function resetGame() {
    ball.x = canvas.width / 2;
    // ball.x = paddle.x + (paddle.width / 2);
    ball.y = canvas.height - (paddle.height + ball.radius * 3);
    // ball.y = canvas.height / 2;

    const angle = (Math.PI / 4) + Math.random() * (Math.PI / 2) + Math.PI;
    ball.dx = Math.cos(angle);
    ball.dy = Math.sin(angle);
    initBlocks();
}

// ゲーム内部処理
function updateGame(action) {
    let reward = rewardState.time;
    let done = false;

    // バー操作
    if (action === 0) paddle.x -= paddle.speed;
    if (action === 2) paddle.x += paddle.speed;

    paddle.x = Math.max(0, Math.min(canvas.width - paddle.width, paddle.x));

    // ボール移動
    // ball.dy += 0.1;
    // ball.x += ball.dx * ball.speed;
    // ball.y += ball.dy * ball.speed;

    // サブステップ
    const stepSize = ball.radius - 1;
    const subSteps = Math.ceil(ball.speed / stepSize);
    const vx = (ball.dx * ball.speed) / subSteps;
    const vy = (ball.dy * ball.speed) / subSteps;

    // サブステップループ
    for (let i = 0; i < subSteps; i++) {
        ball.x += vx;
        ball.y += vy;

        let collided = false;

        for (let c = 0; c < blockColumnCount; c++) {
            for (let r = 0; r < blockRowCount; r++) {
                let b = blocks[c][r];
                if (b.status === 1) {//まだあるブロックだけ
                    if (
                        ball.x + ball.radius > b.x &&//ボールの右端がブロックの左端
                        ball.x - ball.radius < b.x + blockW &&//ボールの左端がブロックの右端以上
                        ball.y + ball.radius > b.y &&//ボールの下端がブロックの上端
                        ball.y - ball.radius < b.y + blockH//ボールの上端がブロックの下端
                        ) {

                            if (ball.x > b.x && ball.x < b.x + blockW) {
                                ball.dy *= -1;
                                ball.y = (ball.dy < 0) ? b.y - ball.radius : b.y + blockH + ball.radius; 
                            } else {
                                ball.dx *= -1;
                                ball.x = (ball.dx < 0) ? b.x - ball.radius : b.x + blockW + ball.radius;
                            }
                            //跳ね返して
                            b.status = 0;//消して
                            reward += rewardState.break;//報酬追加
                            collided = true;
                            break;
                        }
                }
            }

        }
        if (collided) break;

        // ボール壁反射
        if (ball.x < ball.radius) {
            ball.x = ball.radius;//めり込まないように一番外に配置
            ball.dx *= -1;//反転
            collided = true;
        } else if (ball.x > canvas.width - ball.radius) {
            ball.x = canvas.width - ball.radius;//めり込まないように一番外に配置
            ball.dx *= -1;//反転
            collided = true;
        }
        if (ball.y < ball.radius) {
            ball.y = ball.radius;//めり込まないように一番外に配置
            ball.dy *= -1;//反転
            collided = true;
        }

        // ボールバー反射
        if (ball.y + ball.dy > canvas.height - paddle.height - ball.radius) {
            if (ball.x > paddle.x && ball.x < paddle.x + paddle.width && ball.dy > 0) {
                let hitPos = (ball.x - (paddle.x + paddle.width / 2)) / (paddle.width / 2);//(paddle.x+paddle.width/2)はバーの中心の座標 ball.x-で中心からの距離
                let reflectAngle = hitPos * (Math.PI / 3);//反射角を45～60度にする

                ball.dx = Math.sin(reflectAngle);
                ball.dy = -Math.cos(reflectAngle);

                ball.y = canvas.height - paddle.height - ball.radius;//めり込み防止

                reward = rewardState.hit;

                // 落としたら
            } else if (ball.y > canvas.height) {
                reward = rewardState.drop;
                done = true;

                flashColor = 'rgba(255, 0, 0, 0.3)';

                resetGame();
                return {reward, done};
            }
        }
        if (collided) break;
    }

    // 全消し
    let activeBlocks = blocks.flat().filter(b => b.status === 1).length;//ブロックのstatusが1状態の数
    if (activeBlocks === 0) {
        reward += rewardState.all;
        done = true;

        console.log("%c★ ALL CLEAR! ★", "color: yellow; background: black; font-weight: bold;");
        flashColor = 'rgba(255, 255, 255, 0.5)';

        resetGame();
    }

    return {reward, done};
}

// ゲーム描画
let flashColor = '';

function draw() {
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    // ブロック
    for (let c = 0; c < blockColumnCount; c++) {
        for (let r = 0; r < blockRowCount; r++) {
            if (blocks[c][r].status === 1) {
                ctx.fillStyle = "#00a6ff";
                ctx.fillRect(blocks[c][r].x, blocks[c][r].y, blockW, blockH);
            }
        }
        
    }

    // ボール
    ctx.beginPath();
    ctx.arc(ball.x, ball.y, ball.radius, 0, Math.PI * 2);
    ctx.fillStyle = '#ffa500';
    ctx.fill();
    ctx.closePath();

    // バー
    ctx.fillStyle = '#ffc0cb';
    ctx.fillRect(paddle.x, canvas.height - paddle.height, paddle.width, paddle.height);

    if (flashColor !== '') {
        ctx.fillStyle = flashColor;
        ctx.fillRect(0, 0, canvas.width, canvas.height);
        flashColor = '';
    }
}

resetGame();

// コントロールパネル
//ステータス
const paddleWidth = document.getElementById('paddleWidth');
const paddleSpeed = document.getElementById('paddleSpeed');
const ballSize = document.getElementById('ballSize');
const ballSpeed = document.getElementById('ballSpeed');

paddleWidth.addEventListener('input', (e) => {//スライダーを変更したら
    paddle.width = e.target.value * 1.4 + 10;
});
paddleSpeed.addEventListener('input', (e) => {//スライダーを変更したら
    paddle.speed = e.target.value / 4 + 2;
});
ballSize.addEventListener('input', (e) => {//スライダーを変更したら
    ball.radius = e.target.value / 2 + 1;
});
ballSpeed.addEventListener('input', (e) => {//スライダーを変更したら
    ball.speed = e.target.value / 2 + 1;
});

//性格
let persoonality = {
    gamma: 0.9,
    learningRate: 0.001
};
//スライダーを変更したら
const gammaSlider = document.getElementById('gamma');
const lrSlider = document.getElementById('learningRate');
gammaSlider.addEventListener('input', updatePersonality);
lrSlider.addEventListener('input', updatePersonality);

updatePersonality();

function updatePersonality() {
    const gammaInput = document.getElementById('gamma').value;
    const lrInput = document.getElementById('learningRate').value;

    persoonality.gamma = 0.5 + (gammaInput / 100) * 0.49,//0.5~0.99に変換
    persoonality.learningRate = 0.01 * Math.pow(0.1, lrInput / 50)//0.01~0.0001に変換
    console.log(persoonality.gamma + "" + persoonality.learningRate);
}
// リセットボタン
document.getElementById('perspnalityResetBtn').addEventListener('click', () => {
    setTimeout(() => {
        updatePersonality();
    }, 0);
});