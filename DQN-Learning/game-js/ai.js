class ReplayBuffer {
    constructor(capacity) {
        this.capacity = capacity;
        this.buffer = [];
    }

    push(experience) {
        if (this.buffer.length >= this.capacity) {
            this.buffer.shift();
        }
        this.buffer.push(experience);
    }

    sample(batchSize) {
        const shuffled = [...this.buffer].sort(() => 0.5 - Math.random());
        return shuffled.slice(0, batchSize);
    }

    get length() {
        return this.buffer.length;
    }
}

// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// sequentialシンプルな書き方
// 積み上げるように作っていくから簡単だけど出口が一つしか作れない
// 今回はニューロンモニターのために途中のデータ取得用に出口を2つ作りたいから使わない

// function createModel() {
//     const model = tf.sequential();//ネットワーク作成 様々なテンソルメソッドを追加 tfはテンソルフロー

// // 入力層
// model.add(tf.layers.dense({//デンスというタイプの層を指定
//     units:128,//ユニット(ニューロン)を128個
//     activation:'relu',//活性化関数の種類をマイナスだったら0に変換するReLU活性化関数に指定
//     inputShape:[7]//6つの入力(ボールxy、速度xy、バーx、バー長さ、重力)
// }));

// // 中間層
// model.add(tf.layers.dense({//デンスというタイプの層を指定
//     units:128,//ユニット(ニューロン)を128個
//     activation:'relu',//活性化関数の種類をマイナスだったら0に変換するReLU活性化関数に指定
// }));

// // 出力層
// model.add(tf.layers.dense({//デンスというタイプの層を指定
//     units:3,//ユニット(ニューロン)を3個(左、静止、右のQ値を出すため)
//     activation:'linear',//活性化関数の種類を無変換のlinearに指定
// }));

// model.compile({
//     optimizer:tf.train.adam(0.001),//Adam最適化アルゴリズムと学習率
//     loss:'meanSquaredError'//損失関数 (TD誤差を計算するため)
// });

// return model;
// }

// //メインネットワークとターゲットネットワーク同じものを作る
// let mainModel = createModel();
// let targetModel = createModel();

// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
let model;
let visualizationModel;
let targetModel;


function createModel() {
    // 入力層
    const input = tf.input({shape: [6]});

    // 中間層
    const hidden = tf.layers.dense({
        units: 128,
        activation: 'relu'
    }).apply(input);

    // 出力層
    const output = tf.layers.dense({
        units: 3,
        activation: 'linear'
    }).apply(hidden);

    // メインネットワーク用モデル
    model = tf.model({inputs: input, outputs: output});

    // ニューロンモニター用モデル
    visualizationModel = tf.model({inputs: input, outputs: hidden});

    model.compile({
        optimizer:tf.train.adam(0.001),////Adam最適化アルゴリズムと学習率
        loss: 'meanSquaredError'//損失関数 (TD誤差を計算するため)
    });

    return { model, visualizationModel};
}

const mainResult = createModel();
let mainModel = mainResult.model;//メインネットワーク
let neuronModel = mainResult.visualizationModel;//モニターネットワーク

const targetResult = createModel();
targetModel = targetResult.model;//ターゲットネットワーク

const memory = new ReplayBuffer(10000);//capacity10000

// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

async function train(gamma, learningRate, batchSize = 128) {
    if (memory.length < batchSize) {
        return;
    }

    mainModel.optimizer.learningRate = learningRate;//learningRateを更新

    const batch = memory.sample(batchSize);//ReplayBufferのsampleメソッド

    const states = tf.tensor2d(batch.map(d => d.state));//batchの中のstateだけを取り出してテンソルに変換
    const nextStates = tf.tensor2d(batch.map(d => d.nextState));//batchの中のNectStateだけを取り出してテンソルに変換

    const currentQs = mainModel.predict(states);//predict()はテンソルメソッドで左0.5、静止0.1、右0.8のように行動ごとのQ値を計算してくれる
    const nextQs = targetModel.predict(nextStates);//nextQsをtargetModelで計算するのは直近の調整の影響を受けすぎないように

    const nextQsData = await nextQs.array();//計算のために配列に戻す
    const currentQsData = await currentQs.array();

    for (let i = 0; i < batch.length; i++) {
        const {action, reward, done} = batch[i];
        let targetQ = reward;
        if (!done) {
            targetQ += gamma * Math.max(...nextQsData[i]);
        }
        currentQsData[i][action] = targetQ;
    }

    const targetQs = tf.tensor2d(currentQsData);
    await mainModel.fit(states, targetQs, {epochs:1, verbose:0});

    tf.dispose([states, nextStates, currentQs, nextQs, targetQs]);
}

// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
let epsilon = 1.0;
const epsilonMin = 0.01;//最終的に1％まで減らす
const epsilonDecayLevel = {
    0:0.9999,
    1:0.99995,
    2:0.99999,
    3:1
};
let epsilonDecay = 0.99995;

const epsilonRange = document.getElementById('epsilonRange');
const epsilonFix = document.getElementById('epsilonFix');
const epsilonPercent = document.getElementById('epsilonPercent');
epsilonRange.addEventListener('input', (e) => {//Rangeを動かしたら
    epsilon = parseFloat(e.target.value) / 100;//eはイベントでeの中のtarget(スライダー)の中のvalue(値)
    epsilonRange.style.setProperty('--pos', `${epsilon * 100}%`);
    epsilonPercent.textContent = `${Math.round(epsilon * 100)}%`;
});

epsilonFix.addEventListener('input', (e) => {//スライダーを変更したら
    epsilonDecay = epsilonDecayLevel[e.target.value];
    console.log(`イプシロン率を${epsilonDecay}に変更`);
});

function decideAction(state) {//引数はcurrentState状況A
    if (epsilon > epsilonMin) {//最小値に達していなかったら
        epsilon *= epsilonDecay;//イプシロン率を減少させる
        if (stepCount % 100 === 0) {//重くなるから100に1回スライダー更新
            epsilonRange.value = epsilon * 100;
            epsilonRange.style.setProperty('--pos', `${epsilon * 100}%`);
            epsilonPercent.textContent = `${Math.round(epsilon * 100)}%`;
        }
    }

    if (Math.random() < epsilon) {//探索率(epsilon) epsilonの確率で探索する
        return Math.floor(Math.random() * 3);//012をランダムで返す 0:左, 1:静止, 2:右
    }

    return tf.tidy(() => {//tidyで囲むと使い終わったデータを自動で消してくれる
        const stateTensor = tf.tensor2d([state]);//状況Aをテンソルに変換

        // メインモデルで行動を決定
        const prediction = mainModel.predict(stateTensor);//predict()で状況AのQ値をメインネットワークで計算 例:左0.5、静止0.1、右0.8
        // trainメソッドとやっていることは同じで、predictは2次配列で渡さないといけなく、今回は入力値1セットの1次配列だから[]で囲って2次配列にしている

        // モニター用モデルでニューロン状態を抜き出す
        const activations = neuronModel.predict(stateTensor);
        // 中間層ニューロンモニターに描写
        drawHiddenNeurons(activations.dataSync());//dataSync()でjsが扱えるデータに変換する

        // 出力層ニューロンモニターに描写
        drawOutputNeurons(prediction.dataSync());//3つの出力Q値が入ってるpredictionを引数にする dataSync()でjsが扱えるデータに変換する

        // 一番Q値が大きい行動を返す
        return prediction.argMax(1).dataSync()[0];//argMax()は0は縦(左, 左, 左) 1は横(左, 静止, 右)を比較　dataSync()[0]は[2]のようなデータで返ってくるから[0]で配列をほどく
    });
}

// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

let stepCount = 0;

function updateTargetModel() {
    stepCount++;

    if (stepCount % 1000 === 0 && stepCount > 0) {
        targetModel.setWeights(mainModel.getWeights());
        console.log("ターゲットネットワーク更新：" + stepCount);
    }
}