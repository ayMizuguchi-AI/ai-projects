import * as THREE from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { VRMLoaderPlugin } from '@pixiv/three-vrm';

const backendUrl = `http://${window.location.hostname}:8080`;

// --- 基本設定 (シーン、カメラ、レンダラー) ---
const scene = new THREE.Scene();
const camera = new THREE.PerspectiveCamera(30, window.innerWidth / window.innerHeight, 0.1, 20.0);
camera.position.set(0.3, 1.2, 2.75); // 顔のあたりにカメラを配置 左右, 高さ, 前後
camera.lookAt(-0.38, 1.2, 0);


const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
renderer.setSize(window.innerWidth, window.innerHeight);
renderer.setPixelRatio(window.devicePixelRatio);
renderer.setClearColor(0x000000, 0); //背景色
document.body.appendChild(renderer.domElement);

// ライト
const light = new THREE.DirectionalLight(0xffffff, 1.0);
light.position.set(1.0, 1.0, 1.0).normalize();
scene.add(light);



// --- VRMの読み込み ---
let currentVrm = null;
const mouthTarget = { aa: 0, ih: 0, ou: 0, ee: 0, oh: 0 };
const neckTarget = { x: 0, y: 0, z: 0 };
const loader = new GLTFLoader();
loader.register((parser) => new VRMLoaderPlugin(parser));

loader.load(
    './etc/sample.vrm', // ファイル名が合っているか確認
    (gltf) => {
        const vrm = gltf.userData.vrm;
        currentVrm = vrm;
        scene.add(vrm.scene);
        placeBubbleOnce();

        console.log('【読み込み完了！】');
    },
);

const clock = new THREE.Clock();


let audioContext, analyser, dataArray;

// 音声を解析して口パクに変換する関数
function setupLipSync(audioElement) {
    if (!audioContext) {
        audioContext = new (window.AudioContext || window.webkitAudioContext)();
        analyser = audioContext.createAnalyser();
    }
    const source = audioContext.createMediaElementSource(audioElement);
    source.connect(analyser);
    analyser.connect(audioContext.destination);
    analyser.fftSize = 256;
    dataArray = new Uint8Array(analyser.frequencyBinCount);
}

let isAsking = false;
let isPlayingAudio = false;

let talkAnimationWeight = 0; // 0なら待機ポーズ、1なら再生中ポーズ

// 読み上げ
async function reading(text) {
    if (!text || isAsking) return;
    isAsking = true;

    try {
        // const response = await fetch('http://127.0.0.1:8080/read', {
        const response = await fetch(`${backendUrl}/read`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ text: text })
        });
        const data = await response.json();
        const audioUrl = `data:audio/wav;base64,${data.audio}`;
        const audio = new Audio(audioUrl);
        isPlayingAudio = true;

        setupLipSync(audio);
        audio.play();
    } catch (e) {
        console.error("読み込みエラー：", e);
    } finally {
        isAsking = false;
        dataArray.fill(0);
        mouthTarget.aa = 0;
    }
}

// 考え中データ
const thinkingVoices = [
    './etc/うーん.wav',
    './etc/えーっと.wav',
    './etc/たしかにー.wav'
];
const thinkingPoses = [
    { x: -5 * (Math.PI / 180), y: -10 * (Math.PI / 180), z: 15 * (Math.PI / 180) },  // 左にかしげる
    { x: -5 * (Math.PI / 180), y: 10 * (Math.PI / 180), z: -15 * (Math.PI / 180) }, // 右にかしげる
    { x: 20 * (Math.PI / 180), y: 0, z: 0 }                          // 少し上を向いて考える
];

const bubble = document.getElementById('bubble');
// geminiに送信
async function askAi(text) { //askAi(text)が入力
    if (!text || isAsking) return;
    isAsking = true;

    // 吹き出し表示
    bubble.style.display = 'block';
    placeBubbleOnce();

    // ランダムで首を傾げる
    const poseIndex = Math.floor(Math.random() * thinkingPoses.length);
    // console.log(poseIndex);
    const randomPose = thinkingPoses[poseIndex];
    neckTarget.x = randomPose.x;
    neckTarget.y = randomPose.y;
    neckTarget.z = randomPose.z;

    // ランダムで準備中音声を再生
    const randomVoice = thinkingVoices[Math.floor(Math.random() * thinkingVoices.length)];
    const thinkingAudio = new Audio(randomVoice);
    setupLipSync(thinkingAudio);
    thinkingAudio.play();

    console.log("【考え中...】");

    const aiMsgDiv = document.createElement('div');
    aiMsgDiv.className = 'line-msg msg-ai';
    aiMsgDiv.innerText = '...'; // 考え中演出
    lineLog.appendChild(aiMsgDiv);
    lineLog.scrollTop = lineLog.scrollHeight;

    // バックエンドに送信
    try {
        // const response = await fetch('http://127.0.0.1:8080/chat', {
        const response = await fetch(`${backendUrl}/chat`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message: text })
        });


        const reader = response.body.getReader();//送られてきたデータの受付
        const decoder = new TextDecoder();
        let audioQueue = [];//再生待ち音声データのキュー
        let isPlaying = false;//再生中フラグ
        let partialLine = ""//途中でちぎれて届いたテキストの保管

        async function playNext() {
            if (audioQueue.length > 0 && !isPlaying) {//キューの中身があり、現在何も再生していなかったら
                neckTarget.x = 0;//首戻す
                neckTarget.y = 0;//首戻す
                neckTarget.z = 0;//首戻す
                bubble.style.display = 'none';//吹き出し消す
                isPlaying = true;//音声再生中のフラグ 次の音声を止めておく
                isPlayingAudio = true;
                const audioData = audioQueue.shift();//キューの一番前のデータをaudioDataに取り出す
                const audio = new Audio(`data:audio/wav;base64,${audioData}`);//再生準備

                setupLipSync(audio);//口パク関数に音声データを入れる
                audio.play();//再生
                audio.onended = () => {//再生終わった時のイベントリスナー
                    isPlaying = false;//再生中フラグを下ろす
                    isPlayingAudio = false;
                    playNext();//次の音声へ
                };
            } else if (audioQueue.length === 0 && !isPlaying) {
                // キューが空っぽで、再生も完全に終わったらここを通る
                isPlayingAudio = false; //念のためここでも手振りを確実に止める
            }
        }

        while (true) {
            //データの1小片を受け取り
            const { done, value } = await reader.read();//doneはデータ送信がすべて終わったかのフラグ、valueは生データ
            if (done) break;//データ送信をすべて受け取ったらループを抜ける

            const chunk = decoder.decode(value, { stream: true });//受け取った生データをテキストに変換 streamはデータが千切れて文字化けしないように
            const lines = (partialLine + chunk).split('\n');//\nまでのデータをlinesに

            partialLine = lines.pop();//余ったデータをpartialLineに入れる

            for (let line of lines) {//linesから一行lineずつデータを順番に取り出す
                line = line.trim();//trim()で余計なスペースや改行を消して整える
                if (!line.trim()) continue;//trim()した結果中身がなくなったらバグらないように次に進む

                if (line.startsWith(';')) {//ノイズを消す
                    line = line.substring(line.indexOf('{'));
                }

                try {
                    const data = JSON.parse(line);//綺麗になったlineをオブジェクトに変換してdataに入れる
                    console.log(data.answer);//AIのセリフ部分を表示

                    if (aiMsgDiv) {
                        if (aiMsgDiv.innerText === '...') {
                            aiMsgDiv.innerText = '';
                        }
                        aiMsgDiv.innerText += data.answer;
                        lineLog.scrollTop = lineLog.scrollHeight;
                    }

                    audioQueue.push(data.audio);//音声データをキューに入れる
                    playNext();//再生関数を呼ぶ
                } catch (e) {
                    console.warn("スキップした行：", line.substring(0, 20) + "...");
                }
            }
        }
    } catch (e) {
        console.error("通信エラー：", e);
        neckTarget.x = 0;//首戻す
        neckTarget.y = 0;//首戻す
        neckTarget.z = 0;//首戻す
    } finally {
        isAsking = false;
        console.log('【終了】');
    }
}


// 画面サイズ調整
window.addEventListener('resize', () => {
    const width = window.innerWidth;
    const height = window.innerHeight;

    renderer.setSize(width, height);

    camera.aspect = width / height;
    camera.updateProjectionMatrix();
    placeBubbleOnce();
});

// アニメーションループ
function animate() {
    requestAnimationFrame(animate);
    const deltaTime = clock.getDelta();

    if (currentVrm) {
        if (analyser) {
            analyser.getByteFrequencyData(dataArray);
            let volume = 0;
            for (let i = 0; i < dataArray.length; i++) { volume += dataArray[i]; }
            volume /= dataArray.length; // 平均音量

            // 音量が一定以上なら「あ(aa)」の口にする
            if (volume < 20) {
                mouthTarget.aa = 0;
            } else {
                mouthTarget.aa = Math.min((volume - 20) / 100, 1.0);
            }
        }

        const keys = ['aa', 'ih', 'ou', 'ee', 'oh'];
        keys.forEach(key => {
            const currentValue = currentVrm.expressionManager.getValue(key);
            const targetValue = mouthTarget[key];

            const speed = targetValue === 0 ? 0.9 : 0.9;

            const lerpValue = THREE.MathUtils.lerp(currentValue, mouthTarget[key], speed);
            currentVrm.expressionManager.setValue(key, lerpValue);
        });

        const humanoid = currentVrm.humanoid;



        // 2. 呼吸の揺れ（これは scene 全体を回すので確実）
        currentVrm.scene.rotation.x = Math.sin(Date.now() * 0.005) * 0.01;
        const time = performance.now() * 0.001; // 秒単位の時間

        const bones = {
            leftUpperArm: humanoid.getNormalizedBoneNode('leftUpperArm'),
            rightUpperArm: humanoid.getNormalizedBoneNode('rightUpperArm'),
            leftLowerArm: humanoid.getNormalizedBoneNode('leftLowerArm'),
            rightLowerArm: humanoid.getNormalizedBoneNode('rightLowerArm'),
            leftHand: humanoid.getNormalizedBoneNode('leftHand'),
            rightHand: humanoid.getNormalizedBoneNode('rightHand'),

            spine: humanoid.getNormalizedBoneNode('spine'),
            chest: humanoid.getNormalizedBoneNode('chest'),
            upperChest: humanoid.getNormalizedBoneNode('upperChest'),

            head: humanoid.getNormalizedBoneNode('head'),

            hips: humanoid.getNormalizedBoneNode('hips'),
            leftUpperLeg: humanoid.getNormalizedBoneNode('leftUpperLeg'),
            rightUpperLeg: humanoid.getNormalizedBoneNode('rightUpperLeg'),
            leftLowerLeg: humanoid.getNormalizedBoneNode('leftLowerLeg'),
            rightLowerLeg: humanoid.getNormalizedBoneNode('rightLowerLeg'),

            neckBone: humanoid.getNormalizedBoneNode('neck')
        };

        // 背骨
        if (bones.spine) bones.spine.rotation.x = 0.1;       // 軽く前傾
        if (bones.chest) bones.chest.rotation.x = 0.2;       // 丸める
        if (bones.upperChest) bones.upperChest.rotation.x = 0.2; // さらに丸める

        if (bones.head) bones.head.rotation.x = -0.3; // 顔を少し上げる
        if (bones.neckBone) bones.neckBone.rotation.z = 0.1;

        const epicenter = Math.sin(time * 40) * 0.02; // 3は速さ、0.2は振れ幅
        if (bones.hips && bones.leftUpperLeg && bones.leftLowerLeg) {
            // 足の付け根を90度曲げる（座る動作）
            const sitAngle = -Math.PI / 2.2; // 約70〜90度（背景に合わせて調整）
            bones.leftUpperLeg.rotation.x = -Math.PI / 2.3 + epicenter;
            bones.rightUpperLeg.rotation.x = -Math.PI / 2.1 + epicenter * 0.2;
            bones.leftUpperLeg.rotation.z = -Math.PI / 0.51;
            bones.rightUpperLeg.rotation.z = Math.PI / 0.52;

            // 膝（ひざ）を曲げる
            const kneeAngle = Math.PI / 2.2;
            bones.leftLowerLeg.rotation.x = kneeAngle;
            bones.rightLowerLeg.rotation.x = kneeAngle;
        }

        // 指のボーン名をリスト化
        const fingerKeys = [
            'Thumb', 'Index', 'Middle', 'Ring', 'Little' // 親指、人差し指、中指、薬指、小指
        ];
        const fingerParts = ['Proximal', 'Intermediate', 'Distal']; // 付け根、第2、第3関節

        if (currentVrm) {
            const humanoid = currentVrm.humanoid;

            // 左右の手に対して処理
            ['left', 'right'].forEach(side => {
                fingerKeys.forEach(finger => {
                    fingerParts.forEach(part => {
                        // ボーン名を作成（例：leftIndexProximal）
                        const boneName = `${side}${finger}${part}`;
                        const bone = humanoid.getNormalizedBoneNode(boneName);

                        if (bone) {
                            bone.rotation.z = (side === 'left') ? -0.2 : 0.2;
                        }
                    });
                });
            });
            // 首傾げ
            if (bones.neckBone) {
                const speed = neckTarget.z === 0 ? 0.01 : 0.01;

                bones.neckBone.rotation.x = THREE.MathUtils.lerp(bones.neckBone.rotation.x, neckTarget.x, speed);
                bones.neckBone.rotation.y = THREE.MathUtils.lerp(bones.neckBone.rotation.y, neckTarget.y, speed);
                bones.neckBone.rotation.z = THREE.MathUtils.lerp(bones.neckBone.rotation.z, neckTarget.z, speed);
            }
            const weightSpeed = deltaTime * 5.0;
            talkAnimationWeight = THREE.MathUtils.lerp(talkAnimationWeight, isPlayingAudio ? 1 : 0, weightSpeed);

            if (bones.leftUpperArm) bones.leftUpperArm.quaternion.setFromEuler(new THREE.Euler(-0.35, -0.6, -1.5));
            if (bones.leftLowerArm) bones.leftLowerArm.quaternion.setFromEuler(new THREE.Euler(0, -1, 0));

            if (bones.rightUpperArm && bones.rightLowerArm && bones.rightHand) {
                // ゆらゆら用の値（常に計算しておく）
                const swing = Math.sin(time * 5) * 0.3;

                // ① 待機時のポーズ (Base)
                const qBaseUpper = new THREE.Quaternion().setFromEuler(new THREE.Euler(-0.3, 0.5, 1.5));
                const qBaseLower = new THREE.Quaternion().setFromEuler(new THREE.Euler(0, 1, 0));
                const qBaseHand = new THREE.Quaternion().setFromEuler(new THREE.Euler(0.1, 0, 0));

                // ② 音声再生中のポーズ (Talk)
                const qTalkUpper = new THREE.Quaternion().setFromEuler(new THREE.Euler(-1.3, -0.8, 1.0 + swing * 0.1));
                const qTalkLower = new THREE.Quaternion().setFromEuler(new THREE.Euler(0, 1, 0.7 + swing * 0.5));
                const qTalkHand = new THREE.Quaternion().setFromEuler(new THREE.Euler(-0.8, 0, -0.5 + swing));

                // ③ 2つのポーズを talkAnimationWeight の割合で混ぜ合わせる（slerp補間）
                bones.rightUpperArm.quaternion.copy(qBaseUpper).slerp(qTalkUpper, talkAnimationWeight);
                bones.rightLowerArm.quaternion.copy(qBaseLower).slerp(qTalkLower, talkAnimationWeight);
                bones.rightHand.quaternion.copy(qBaseHand).slerp(qTalkHand, talkAnimationWeight);
            }
        }
        // // 3. VRMの全機能を更新
        currentVrm.update(deltaTime);
    }
    renderer.render(scene, camera);
}

animate();

// メッセージ送信
const message = document.getElementById('message');
// 読み上げ
const readingBtn = document.getElementById('reading');
readingBtn.addEventListener('click', () => {
    reading(message.value);
    message.value = '';
});

// Gemini
const send = document.getElementById('send');
send.addEventListener('click', () => {
    if (isAsking) return;
    messageLog();
    console.log(message.value);
    askAi(message.value);
    message.value = '';
});
document.addEventListener('keydown', (event) => {
    if (event.key === 'Enter' && message.value) {
        if (isAsking) return;
        messageLog();
        console.log(message.value);
        askAi(message.value);
        message.value = '';
    }
});


// 音声認識
const voiceRecognition = document.getElementById('voiceRecognition');

const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
if (!SpeechRecognition) {
    console.log("ブラウザが音声認識に対応してないかも");
} else {
    const recognition = new SpeechRecognition();

    recognition.lang = 'ja-JP';
    recognition.interimResults = false;
    recognition.continuous = true;

    voiceRecognition.onclick = () => {
        recognition.start();
        console.log("【音声入力開始】");
    }

    recognition.onresult = (e) => {
        const lastIndex = e.results.length - 1;
        const text = e.results[lastIndex][0].transcript;

        console.log("音声認識：" + text);
        lineLog.innerHTML += `<div class="line-msg msg-user">${text}</div>`;
        lineLog.scrollTop = lineLog.scrollHeight;
        askAi(text);
    }
}

// 吹き出し
function placeBubbleOnce() {
    const head = currentVrm.humanoid.getNormalizedBoneNode('head');
    const vector = new THREE.Vector3();

    head.getWorldPosition(vector);

    vector.y += 0.25;

    vector.project(camera);

    const x = (vector.x * 0.5 + 0.5) * window.innerWidth;
    const y = (vector.y * -0.5 + 0.5) * window.innerHeight;

    const bubble = document.getElementById('bubble');
    bubble.style.left = `${x}px`;
    bubble.style.top = `${y}px`;
}
const lineLog = document.getElementById('lineLog');
// ログに表示
function messageLog() {
    if (isAsking) return;
    const text = message.value.trim();
    if (!text) return;

    lineLog.innerHTML += `<div class="line-msg msg-user">${text}</div>`;

    lineLog.scrollTop = lineLog.scrollHeight;
}
