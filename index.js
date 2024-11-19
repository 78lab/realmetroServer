const express = require('express');
const axios = require('axios');
const admin = require('firebase-admin');
const serviceAccount = require('./firedemo2405-firebase-adminsdk-f9x98-a551cf9794.json'); // Firebase 서비스 계정 키

require('dotenv').config();
SEOUL_API_KEY = process.env.SEOUL_API_KEY;

const TRAIN_DATA_PATH = 'realtimePositions'

// Firebase 초기화
admin.initializeApp({
  credential: admin.credential.cert(serviceAccount),
});

const db = admin.firestore(); // Firestore 데이터베이스 참조

const app = express();
app.use(express.json()); // JSON 파싱을 위한 미들웨어

let updateInterval = null;
let isUpdating = false; // 업데이트 상태 관리
let mLine = 0;

// userCount가 변화할 때마다 업데이트
db.doc('metadata/userCount').onSnapshot(async (docSnapshot) => {
  const userCount = docSnapshot.data().userCount;
  mLine = docSnapshot.data().subwayLine;

  console.log('subwayLine name changed mLine,userCount:', mLine,userCount,isUpdating);
  if (userCount > 0 && mLine > 0 && mLine < 10) {
    await stopUpdate();
    await startUpdate();
  } else if (isUpdating) {
    await stopUpdate();
  }
});

// userCount가 변화할 때마다 업데이트
// db.doc('metadata/userCount').onSnapshot(async (docSnapshot) => {
//   // const userCount = docSnapshot.data().userCount;
//   const line01 = docSnapshot.data().line01;
//   const line02 = docSnapshot.data().line02;
//   const line03 = docSnapshot.data().line03;
//   const line04 = docSnapshot.data().line04;
//   const line05 = docSnapshot.data().line05;
//   const line06 = docSnapshot.data().line06;
//   const line07 = docSnapshot.data().line07;
//   const line08 = docSnapshot.data().line08;
//   const line09 = docSnapshot.data().line09;
//   console.log('User count changed:', line01,line02,line03,line04,line05,line06,line07,line08,line09);
//   // if (userCount > 0 && !isUpdating) {
//   //   await startUpdate();
//   // } else if (userCount === 0 && isUpdating) {
//   //   await stopUpdate();
//   // }
// });

async function startUpdate() {
  updateInterval = setInterval(()=>{
    updateSubwayData().catch((error) => {
      console.error('Error updateSubwayData:', error);
    });
  }, 10000); // 10초마다 실행
  isUpdating = true;
  console.log('Starting real-time data update...',isUpdating);
  await clearCollection(TRAIN_DATA_PATH); // 예: trainData 컬렉션을 초기화
}

async function stopUpdate() {
  clearInterval(updateInterval); // 주기적 업데이트 중지
  updateInterval = null;
  isUpdating = false;
  console.log('Stopping real-time data update...',isUpdating);
}

// 업데이트 시작 전에 해당 컬렉션을 초기화하는 함수
async function clearCollection(collectionPath) {
  const collectionRef = db.collection(collectionPath);
  const snapshot = await collectionRef.get();
  
  if (!snapshot.empty) {
    const batch = db.batch(); // Batch 작업을 사용하여 한 번에 처리

    snapshot.docs.forEach((doc) => {
      batch.delete(doc.ref); // 문서 삭제
    });

    await batch.commit(); // 배치 커밋으로 삭제 완료
    console.log(`Cleared collection: ${collectionPath}`);
  } else {
    console.log(`Collection is already empty: ${collectionPath}`);
  }
}


// 지하철 데이터를 Firestore에 저장하는 함수
const updateSubwayData = async () => {

  try {
    let realtimePositionApiUrl = `http://swopenAPI.seoul.go.kr/api/subway/${SEOUL_API_KEY}/json/realtimePosition/0/300/${mLine}%ED%98%B8%EC%84%A0`
    console.log(`url: ${realtimePositionApiUrl}`)
    const response = await axios.get(realtimePositionApiUrl); // 지하철 API 호출
    const trainData = response.data; // 지하철 API에서 받은 데이터
    console.log(`data: ${trainData}`)
    // Firestore에 데이터 저장

    if(trainData && trainData.realtimePositionList && trainData.realtimePositionList.length > 0){
      const batch = db.batch();

      trainData.realtimePositionList.forEach(train => {
          console.log(`train:${train.trainNo}`)
        const trainRef = db.collection(TRAIN_DATA_PATH).doc(train.trainNo);
        batch.set(trainRef, {
          ...train,
          timestamp: new Date(),
        }, { merge: true });
      });
      
      await batch.commit(); // Firestore에 일괄 저장
      console.log('Train data updated in Firestore!');
    }else{
      console.log('No train data to update.');
    }

  } catch (error) {
    console.error('Error updating train data:', error);
  }
};

// 10초 주기로 데이터를 업데이트 시작
app.post('/start-updates', async (req, res) => {
  const { line } = req.body; // 요청 바디에서 호선 번호 추출

  if (!line) {
    return res.status(400).send({ error: 'Line number is required' });
  }

  mLine = line
  console.log('mLine:', mLine);
  if (mLine > 0) {
    await stopUpdate();
    await startUpdate();
    res.send(`Started updating mLine:${mLine} every 10 seconds.`);
  } else {
    res.send(`Updates are already running or line:${line}`);
  }
});

// 업데이트 중지
app.post('/stop-updates', async (req, res) => {
  if (isUpdating) {
    await stopUpdate();
    res.send('Stopped updating subway data.');
  } else {
    res.send('No updates are currently running.');
  }
});

// 서버 실행
app.listen(3000, () => {
  console.log('Server is running on port 3000 isUpdating:',isUpdating);
});