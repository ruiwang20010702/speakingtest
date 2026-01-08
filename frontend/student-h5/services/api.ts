import { Level, Question, TestResult } from '../types';
import axios from 'axios';

// API 实例
const api = axios.create({
  baseURL: '/api/v1',
});

// 从后端获取题目（优先使用后端数据，失败时使用本地 Mock）
export const getQuestions = async (level: Level, unit: string): Promise<Question[]> => {
  try {
    // 尝试从后端获取题目
    const response = await api.get(`/questions/${level}/${encodeURIComponent(unit)}`);
    const data = response.data;

    // 转换后端数据格式为前端格式
    return data.map((q: any) => ({
      id: q.id.toString(),
      type: q.part === 1 ? 'word' : 'qa',
      text: q.question,
      translation: q.translation,
      image: q.image_url,
      referenceAnswer: q.reference_answer,
    }));
  } catch (error) {
    console.warn('后端题库获取失败，使用本地 Mock 数据:', error);
    // 回退到本地 Mock 数据
    return getLocalMockQuestions(level, unit);
  }
};

// 本地 Mock 数据（备用）
const getLocalMockQuestions = async (level: Level, unit: string): Promise<Question[]> => {
  await new Promise(resolve => setTimeout(resolve, 300));

  const isU1_4 = unit.includes('1-4') || unit.includes('1-3');

  // L0
  if (level === 'L0') {
    const words: Question[] = [
      { id: 'l0w1', type: 'word', text: 'name', translation: '名字', image: '/Word picture/level 0 all_clean/name_签名场景版.png' },
      { id: 'l0w2', type: 'word', text: 'six', translation: '六', image: '/Word picture/level 0 all_clean/six_图标.png' },
      { id: 'l0w3', type: 'word', text: 'hello', translation: '你好', image: '/Word picture/level 0 all_clean/hello_图标.png' },
      { id: 'l0w4', type: 'word', text: 'mom', translation: '妈妈', image: '/Word picture/level 0 all_clean/mom_图标.png' },
      { id: 'l0w5', type: 'word', text: 'dad', translation: '爸爸', image: '/Word picture/level 0 all_clean/hello_图标.png' },
      { id: 'l0w6', type: 'word', text: 'grandma', translation: '奶奶/外婆', image: '/Word picture/level 0 all_clean/grandma_图标.png' },
      { id: 'l0w7', type: 'word', text: 'grandpa', translation: '爷爷/外公', image: '/Word picture/level 0 all_clean/grandpa_图标.png' },
      { id: 'l0w8', type: 'word', text: 'chair', translation: '椅子', image: '/Word picture/level 0 all_clean/chair_图标.png' },
      { id: 'l0w9', type: 'word', text: 'school', translation: '学校', image: '/Word picture/level 0 all_clean/school_图标.png' },
      { id: 'l0w10', type: 'word', text: 'bag', translation: '包', image: '/Word picture/level 0 all_clean/bag_图标.png' },
      { id: 'l0w11', type: 'word', text: 'book', translation: '书', image: '/Word picture/level 0 all_clean/book_图标.png' },
      { id: 'l0w12', type: 'word', text: 'morning', translation: '早上', image: '/Word picture/level 0 all_clean/morning_图标.png' },
      { id: 'l0w13', type: 'word', text: 'afternoon', translation: '下午', image: '/Word picture/level 0 all_clean/afternoon_图标.png' },
      { id: 'l0w14', type: 'word', text: 'good', translation: '好的', image: '/Word picture/level 0 all_clean/good_图标.png' },
      { id: 'l0w15', type: 'word', text: 'clock', translation: '时钟', image: '/Word picture/level 0 all_clean/clock_图标.png' },
      { id: 'l0w16', type: 'word', text: 'today', translation: '今天', image: '/Word picture/level 0 all_clean/today_图标.png' },
      { id: 'l0w17', type: 'word', text: 'watch', translation: '手表', image: '/Word picture/level 0 all_clean/watch_图标.png' },
      { id: 'l0w18', type: 'word', text: 'lemon', translation: '柠檬', image: '/Word picture/level 0 all_clean/lemon_图标.png' },
      { id: 'l0w19', type: 'word', text: 'noodles', translation: '面条', image: '/Word picture/level 0 all_clean/noodles_图标.png' },
      { id: 'l0w20', type: 'word', text: 'rice', translation: '米饭', image: '/Word picture/level 0 all_clean/rice_图标.png' },
    ];
    const qa: Question[] = [
      "What's your name?", "How old are you?", "Who is she?", "Who is he?", "What is this?",
      "What is that?", "How are you?", "When do you eat lunch?", "Do you like apples?", "Do you want to eat rice?"
    ].map((q, i) => ({ id: `l0q${i}`, type: 'qa' as const, text: q, referenceAnswer: 'Answer appropriately' }));
    return [...words, ...qa];
  }

  // L1
  if (level === 'L1') {
    const words_u1_4: Question[] = [
      { id: 'l1w1', type: 'word', text: 'how', translation: '如何', image: `https://loremflickr.com/400/400/how,english` },
      { id: 'l1w2', type: 'word', text: 'night', translation: '夜晚', image: `https://loremflickr.com/400/400/night,english` },
      { id: 'l1w3', type: 'word', text: 'tomato', translation: '番茄', image: `https://loremflickr.com/400/400/tomato,english` },
      { id: 'l1w4', type: 'word', text: 'pencil', translation: '铅笔', image: `https://loremflickr.com/400/400/pencil,english` },
      { id: 'l1w5', type: 'word', text: 'what', translation: '什么', image: `https://loremflickr.com/400/400/what,english` },
      { id: 'l1w6', type: 'word', text: 'moon cake', translation: '月饼', image: `https://loremflickr.com/400/400/mooncake,english` },
      { id: 'l1w7', type: 'word', text: 'breakfast', translation: '早餐', image: `https://loremflickr.com/400/400/breakfast,english` },
      { id: 'l1w8', type: 'word', text: 'lunch', translation: '午餐', image: `https://loremflickr.com/400/400/lunch,english` },
      { id: 'l1w9', type: 'word', text: 'fine', translation: '好的', image: `https://loremflickr.com/400/400/fine,english` },
      { id: 'l1w10', type: 'word', text: 'he', translation: '他', image: `https://loremflickr.com/400/400/he,english` },
      { id: 'l1w11', type: 'word', text: 'book', translation: '书', image: `https://loremflickr.com/400/400/book,english` },
      { id: 'l1w12', type: 'word', text: 'red', translation: '红色', image: `https://loremflickr.com/400/400/red,english` },
      { id: 'l1w13', type: 'word', text: 'homework', translation: '作业', image: `https://loremflickr.com/400/400/homework,english` },
      { id: 'l1w14', type: 'word', text: 'science', translation: '科学', image: `https://loremflickr.com/400/400/science,english` },
      { id: 'l1w15', type: 'word', text: 'party', translation: '派对', image: `https://loremflickr.com/400/400/party,english` },
      { id: 'l1w16', type: 'word', text: 'hen', translation: '母鸡', image: `https://loremflickr.com/400/400/hen,english` },
      { id: 'l1w17', type: 'word', text: 'math', translation: '数学', image: `https://loremflickr.com/400/400/math,english` },
      { id: 'l1w18', type: 'word', text: 'English', translation: '英语', image: `https://loremflickr.com/400/400/english,english` },
      { id: 'l1w19', type: 'word', text: 'movie theater', translation: '电影院', image: `https://loremflickr.com/400/400/movietheater,english` },
      { id: 'l1w20', type: 'word', text: 'polar bear', translation: '北极熊', image: `https://loremflickr.com/400/400/polarbear,english` },
    ];

    const words_u5_8: Question[] = [
      { id: 'l1w1', type: 'word', text: 'pizza', translation: '披萨', image: `https://loremflickr.com/400/400/pizza,english` },
      { id: 'l1w2', type: 'word', text: 'salad', translation: '沙拉', image: `https://loremflickr.com/400/400/salad,english` },
      { id: 'l1w3', type: 'word', text: 'strawberry', translation: '草莓', image: `https://loremflickr.com/400/400/strawberry,english` },
      { id: 'l1w4', type: 'word', text: 'candy', translation: '糖果', image: `https://loremflickr.com/400/400/candy,english` },
      { id: 'l1w5', type: 'word', text: 'jelly bean', translation: '软糖', image: `https://loremflickr.com/400/400/jellybean,english` },
      { id: 'l1w6', type: 'word', text: 'movie', translation: '电影', image: `https://loremflickr.com/400/400/movie,english` },
      { id: 'l1w7', type: 'word', text: 'toy', translation: '玩具', image: `https://loremflickr.com/400/400/toy,english` },
      { id: 'l1w8', type: 'word', text: 'where', translation: '哪里', image: `https://loremflickr.com/400/400/where,english` },
      { id: 'l1w9', type: 'word', text: 'slide', translation: '滑梯', image: `https://loremflickr.com/400/400/slide,english` },
      { id: 'l1w10', type: 'word', text: 'egg', translation: '鸡蛋', image: `https://loremflickr.com/400/400/egg,english` },
      { id: 'l1w11', type: 'word', text: 'next to', translation: '旁边', image: `https://loremflickr.com/400/400/nextto,english` },
      { id: 'l1w12', type: 'word', text: 'inside', translation: '里面', image: `https://loremflickr.com/400/400/inside,english` },
      { id: 'l1w13', type: 'word', text: 'under', translation: '下面', image: `https://loremflickr.com/400/400/under,english` },
      { id: 'l1w14', type: 'word', text: 'starfish', translation: '海星', image: `https://loremflickr.com/400/400/starfish,english` },
      { id: 'l1w15', type: 'word', text: 'jellyfish', translation: '水母', image: `https://loremflickr.com/400/400/jellyfish,english` },
      { id: 'l1w16', type: 'word', text: 'dolphin', translation: '海豚', image: `https://loremflickr.com/400/400/dolphin,english` },
      { id: 'l1w17', type: 'word', text: 'sea turtle', translation: '海龟', image: `https://loremflickr.com/400/400/seaturtle,english` },
      { id: 'l1w18', type: 'word', text: 'thirteen', translation: '十三', image: `https://loremflickr.com/400/400/thirteen,english` },
      { id: 'l1w19', type: 'word', text: 'fourteen', translation: '十四', image: `https://loremflickr.com/400/400/fourteen,english` },
      { id: 'l1w20', type: 'word', text: 'shopping', translation: '购物', image: `https://loremflickr.com/400/400/shopping,english` },
    ];

    const qa_u1_4: Question[] = [
      'How are you?', 'Are you happy today?', 'How old are you?', 'What grade are you in?',
      'Do you have sisters or brothers?', 'How many sisters or brothers do you have?',
      'What can you see in your room?', 'What time is it now?', 'When do you wake up?',
      'What is your favorite food?', 'Do you like English?', 'Can you count from one to twenty?'
    ].map((q, i) => ({ id: `l1q${i}`, type: 'qa' as const, text: q, referenceAnswer: 'Answer appropriately' }));

    const qa_u5_8: Question[] = [
      'What is your favorite food?', 'What is your favorite fruit?', 'Do you like candy?',
      'What kind of candy do you like?', 'Do you like animals?', 'What is your favorite animal?',
      'What animals live in the sea?', 'How many pens do you have?', 'How much is your school bag?',
      'How many people are there in your family?', 'Do you like listen to music?', 'Can you count from one to thirty?'
    ].map((q, i) => ({ id: `l1q${i}`, type: 'qa' as const, text: q, referenceAnswer: 'Answer appropriately' }));

    return isU1_4 ? [...words_u1_4, ...qa_u1_4] : [...words_u5_8, ...qa_u5_8];
  }

  // L2
  if (level === 'L2') {
    const words_u1_4: Question[] = [
      { id: 'l2w1', type: 'word', text: 'sister', translation: '姐妹', image: `https://loremflickr.com/400/400/sister,food` },
      { id: 'l2w2', type: 'word', text: 'family', translation: '家庭', image: `https://loremflickr.com/400/400/family,food` },
      { id: 'l2w3', type: 'word', text: 'friend', translation: '朋友', image: `https://loremflickr.com/400/400/friend,food` },
      { id: 'l2w4', type: 'word', text: 'aunt', translation: '阿姨', image: `https://loremflickr.com/400/400/aunt,food` },
      { id: 'l2w5', type: 'word', text: 'cousin', translation: '表亲', image: `https://loremflickr.com/400/400/cousin,food` },
      { id: 'l2w6', type: 'word', text: 'uncle', translation: '叔叔', image: `https://loremflickr.com/400/400/uncle,food` },
      { id: 'l2w7', type: 'word', text: 'study', translation: '学习', image: `https://loremflickr.com/400/400/study,food` },
      { id: 'l2w8', type: 'word', text: 'vacation', translation: '假期', image: `https://loremflickr.com/400/400/vacation,food` },
      { id: 'l2w9', type: 'word', text: 'fun', translation: '有趣', image: `https://loremflickr.com/400/400/fun,food` },
      { id: 'l2w10', type: 'word', text: 'lesson', translation: '课程', image: `https://loremflickr.com/400/400/lesson,food` },
      { id: 'l2w11', type: 'word', text: 'have to', translation: '必须', image: `https://loremflickr.com/400/400/haveto,food` },
      { id: 'l2w12', type: 'word', text: 'finish', translation: '完成', image: `https://loremflickr.com/400/400/finish,food` },
      { id: 'l2w13', type: 'word', text: 'jump rope', translation: '跳绳', image: `https://loremflickr.com/400/400/jumprope,food` },
      { id: 'l2w14', type: 'word', text: 'week', translation: '星期', image: `https://loremflickr.com/400/400/week,food` },
      { id: 'l2w15', type: 'word', text: 'Monday', translation: '星期一', image: `https://loremflickr.com/400/400/monday,food` },
      { id: 'l2w16', type: 'word', text: 'before', translation: '之前', image: `https://loremflickr.com/400/400/before,food` },
      { id: 'l2w17', type: 'word', text: 'weekend', translation: '周末', image: `https://loremflickr.com/400/400/weekend,food` },
      { id: 'l2w18', type: 'word', text: 'after', translation: '之后', image: `https://loremflickr.com/400/400/after,food` },
      { id: 'l2w19', type: 'word', text: 'plan', translation: '计划', image: `https://loremflickr.com/400/400/plan,food` },
      { id: 'l2w20', type: 'word', text: 'Sunday', translation: '星期天', image: `https://loremflickr.com/400/400/sunday,food` },
    ];

    const words_u5_8: Question[] = [
      { id: 'l2w1', type: 'word', text: 'taste', translation: '味道', image: `https://loremflickr.com/400/400/taste,food` },
      { id: 'l2w2', type: 'word', text: 'sweet', translation: '甜的', image: `https://loremflickr.com/400/400/sweet,food` },
      { id: 'l2w3', type: 'word', text: 'sour', translation: '酸的', image: `https://loremflickr.com/400/400/sour,food` },
      { id: 'l2w4', type: 'word', text: 'pot', translation: '锅', image: `https://loremflickr.com/400/400/pot,food` },
      { id: 'l2w5', type: 'word', text: 'soup', translation: '汤', image: `https://loremflickr.com/400/400/soup,food` },
      { id: 'l2w6', type: 'word', text: 'chopsticks', translation: '筷子', image: `https://loremflickr.com/400/400/chopsticks,food` },
      { id: 'l2w7', type: 'word', text: 'fork', translation: '叉子', image: `https://loremflickr.com/400/400/fork,food` },
      { id: 'l2w8', type: 'word', text: 'table', translation: '桌子', image: `https://loremflickr.com/400/400/table,food` },
      { id: 'l2w9', type: 'word', text: 'left', translation: '左边', image: `https://loremflickr.com/400/400/left,food` },
      { id: 'l2w10', type: 'word', text: 'right', translation: '右边', image: `https://loremflickr.com/400/400/right,food` },
      { id: 'l2w11', type: 'word', text: 'middle', translation: '中间', image: `https://loremflickr.com/400/400/middle,food` },
      { id: 'l2w12', type: 'word', text: 'straight', translation: '直的', image: `https://loremflickr.com/400/400/straight,food` },
      { id: 'l2w13', type: 'word', text: 'near', translation: '附近', image: `https://loremflickr.com/400/400/near,food` },
      { id: 'l2w14', type: 'word', text: 'lost', translation: '迷路', image: `https://loremflickr.com/400/400/lost,food` },
      { id: 'l2w15', type: 'word', text: 'big', translation: '大的', image: `https://loremflickr.com/400/400/big,food` },
      { id: 'l2w16', type: 'word', text: 'small', translation: '小的', image: `https://loremflickr.com/400/400/small,food` },
      { id: 'l2w17', type: 'word', text: 'soft', translation: '软的', image: `https://loremflickr.com/400/400/soft,food` },
      { id: 'l2w18', type: 'word', text: 'hard', translation: '硬的', image: `https://loremflickr.com/400/400/hard,food` },
      { id: 'l2w19', type: 'word', text: 'slow', translation: '慢的', image: `https://loremflickr.com/400/400/slow,food` },
      { id: 'l2w20', type: 'word', text: 'fast', translation: '快的', image: `https://loremflickr.com/400/400/fast,food` },
    ];

    const qa_u1_4: Question[] = [
      'How many people are there in your family?', 'Do you have any sisters?', 'Do you have any brothers?',
      'Who is your best friend?', 'What grade are you in?', 'Did you do your homework?',
      'How was your summer vacation?', 'What do you like to do during summer vacation?', 'What is 1 plus 1?',
      'What do you do on Monday?', 'When is your birthday?', 'Do you have any plan this weekend?'
    ].map((q, i) => ({ id: `l2q${i}`, type: 'qa' as const, text: q, referenceAnswer: 'Answer appropriately' }));

    const qa_u5_8: Question[] = [
      'What\'s your favorite food?', 'How dose it taste?', 'How do you eat food?',
      'Which one is bigger, a cat or a shark?', 'Which one runs faster, a turtle or a horse?',
      'Which grade are you in?', 'What will you learn in first grade?', 'What color is your school bag?',
      'What is your favorite holiday?', 'Do you know when is Christmas?', 'What day is today?',
      'What will you do during summer holiday?'
    ].map((q, i) => ({ id: `l2q${i}`, type: 'qa' as const, text: q, referenceAnswer: 'Answer appropriately' }));

    return isU1_4 ? [...words_u1_4, ...qa_u1_4] : [...words_u5_8, ...qa_u5_8];
  }

  // L3-L6
  const levelData: Record<string, { words: Question[], qa: Question[] }> = {
    'L3': {
      words: [
        { id: 'l3w1', type: 'word', text: 'visit', translation: '拜访', image: `https://loremflickr.com/400/400/visit,nature` },
        { id: 'l3w2', type: 'word', text: 'disappoint', translation: '失望', image: `https://loremflickr.com/400/400/disappoint,nature` },
        { id: 'l3w3', type: 'word', text: 'head to', translation: '前往', image: `https://loremflickr.com/400/400/headto,nature` },
        { id: 'l3w4', type: 'word', text: 'pick up', translation: '捡起', image: `https://loremflickr.com/400/400/pickup,nature` },
        { id: 'l3w5', type: 'word', text: 'hide', translation: '隐藏', image: `https://loremflickr.com/400/400/hide,nature` },
        { id: 'l3w6', type: 'word', text: 'machine', translation: '机器', image: `https://loremflickr.com/400/400/machine,nature` },
        { id: 'l3w7', type: 'word', text: 'unfriendly', translation: '不友好', image: `https://loremflickr.com/400/400/unfriendly,nature` },
        { id: 'l3w8', type: 'word', text: 'Ferris wheel', translation: '摩天轮', image: `https://loremflickr.com/400/400/ferriswheel,nature` },
        { id: 'l3w9', type: 'word', text: 'shake', translation: '摇晃', image: `https://loremflickr.com/400/400/shake,nature` },
        { id: 'l3w10', type: 'word', text: 'a few', translation: '一些', image: `https://loremflickr.com/400/400/afew,nature` },
        { id: 'l3w11', type: 'word', text: 'worksheet', translation: '工作表', image: `https://loremflickr.com/400/400/worksheet,nature` },
        { id: 'l3w12', type: 'word', text: 'come true', translation: '实现', image: `https://loremflickr.com/400/400/cometrue,nature` },
        { id: 'l3w13', type: 'word', text: 'storybook', translation: '故事书', image: `https://loremflickr.com/400/400/storybook,nature` },
        { id: 'l3w14', type: 'word', text: 'knight', translation: '骑士', image: `https://loremflickr.com/400/400/knight,nature` },
        { id: 'l3w15', type: 'word', text: 'activity', translation: '活动', image: `https://loremflickr.com/400/400/activity,nature` },
        { id: 'l3w16', type: 'word', text: 'choose', translation: '选择', image: `https://loremflickr.com/400/400/choose,nature` },
        { id: 'l3w17', type: 'word', text: 'pencil case', translation: '铅笔盒', image: `https://loremflickr.com/400/400/pencilcase,nature` },
        { id: 'l3w18', type: 'word', text: 'shiny', translation: '闪亮的', image: `https://loremflickr.com/400/400/shiny,nature` },
        { id: 'l3w19', type: 'word', text: 'bow tie', translation: '领结', image: `https://loremflickr.com/400/400/bowtie,nature` },
        { id: 'l3w20', type: 'word', text: 'adventure', translation: '冒险', image: `https://loremflickr.com/400/400/adventure,nature` },
      ],
      qa: ['How old are you?', 'How do you feel today?', 'What day is it today?', 'What do you like in your spare time?',
        'Who do you visit on weekend?', 'Will you share your toy?', 'Ever been to an amusement park?', 'Which part do you like best?',
        'When do you usually go to school?', 'Which class do you like best?', 'What want to be in the future?', 'Why?']
        .map((q, i) => ({ id: `l3q${i}`, type: 'qa' as const, text: q, referenceAnswer: 'Answer appropriately' }))
    },
    'L4': {
      words: [
        { id: 'l4w1', type: 'word', text: 'cousin', translation: '表亲', image: `https://loremflickr.com/400/400/cousin,nature` },
        { id: 'l4w2', type: 'word', text: 'niece', translation: '侄女', image: `https://loremflickr.com/400/400/niece,nature` },
        { id: 'l4w3', type: 'word', text: 'nephew', translation: '侄子', image: `https://loremflickr.com/400/400/nephew,nature` },
        { id: 'l4w4', type: 'word', text: 'campsite', translation: '营地', image: `https://loremflickr.com/400/400/campsite,nature` },
        { id: 'l4w5', type: 'word', text: 'intelligent', translation: '聪明的', image: `https://loremflickr.com/400/400/intelligent,nature` },
        { id: 'l4w6', type: 'word', text: 'arrogant', translation: '傲慢的', image: `https://loremflickr.com/400/400/arrogant,nature` },
        { id: 'l4w7', type: 'word', text: 'shy', translation: '害羞的', image: `https://loremflickr.com/400/400/shy,nature` },
        { id: 'l4w8', type: 'word', text: 'gently', translation: '温柔地', image: `https://loremflickr.com/400/400/gently,nature` },
        { id: 'l4w9', type: 'word', text: 'skyscraper', translation: '摩天大楼', image: `https://loremflickr.com/400/400/skyscraper,nature` },
        { id: 'l4w10', type: 'word', text: 'base', translation: '基础', image: `https://loremflickr.com/400/400/base,nature` },
        { id: 'l4w11', type: 'word', text: 'collapse', translation: '倒塌', image: `https://loremflickr.com/400/400/collapse,nature` },
        { id: 'l4w12', type: 'word', text: 'teamwork', translation: '团队合作', image: `https://loremflickr.com/400/400/teamwork,nature` },
        { id: 'l4w13', type: 'word', text: 'lose', translation: '失去', image: `https://loremflickr.com/400/400/lose,nature` },
        { id: 'l4w14', type: 'word', text: 'correct', translation: '正确的', image: `https://loremflickr.com/400/400/correct,nature` },
        { id: 'l4w15', type: 'word', text: 'already', translation: '已经', image: `https://loremflickr.com/400/400/already,nature` },
        { id: 'l4w16', type: 'word', text: 'pity', translation: '可惜', image: `https://loremflickr.com/400/400/pity,nature` },
        { id: 'l4w17', type: 'word', text: 'bait', translation: '鱼饵', image: `https://loremflickr.com/400/400/bait,nature` },
        { id: 'l4w18', type: 'word', text: 'barbecue', translation: '烧烤', image: `https://loremflickr.com/400/400/barbecue,nature` },
        { id: 'l4w19', type: 'word', text: 'alone', translation: '独自', image: `https://loremflickr.com/400/400/alone,nature` },
        { id: 'l4w20', type: 'word', text: 'result', translation: '结果', image: `https://loremflickr.com/400/400/result,nature` },
      ],
      qa: ['How old are you?', 'Which grade are you in?', 'Family count?', 'Do you have a cousin?',
        'Niece relationship?', 'Nephew in family?', 'Have you ever been camping?', 'How was your camping?',
        'First day of school memory?', 'Intro on first day?', 'Subjects in school?', 'Favorite subject?']
        .map((q, i) => ({ id: `l4q${i}`, type: 'qa' as const, text: q, referenceAnswer: 'Answer appropriately' }))
    },
    'L5': {
      words: [
        { id: 'l5w1', type: 'word', text: 'beef broth', translation: '牛肉汤', image: `https://loremflickr.com/400/400/beefbroth,nature` },
        { id: 'l5w2', type: 'word', text: 'baked snails', translation: '烤蜗牛', image: `https://loremflickr.com/400/400/bakedsnails,nature` },
        { id: 'l5w3', type: 'word', text: 'food cart', translation: '餐车', image: `https://loremflickr.com/400/400/foodcart,nature` },
        { id: 'l5w4', type: 'word', text: 'dish', translation: '菜肴', image: `https://loremflickr.com/400/400/dish,nature` },
        { id: 'l5w5', type: 'word', text: 'stinky tofu', translation: '臭豆腐', image: `https://loremflickr.com/400/400/stinkytofu,nature` },
        { id: 'l5w6', type: 'word', text: 'odor', translation: '气味', image: `https://loremflickr.com/400/400/odor,nature` },
        { id: 'l5w7', type: 'word', text: 'beef soup', translation: '牛肉汤', image: `https://loremflickr.com/400/400/beefsoup,nature` },
        { id: 'l5w8', type: 'word', text: 'stand', translation: '摊位', image: `https://loremflickr.com/400/400/stand,nature` },
        { id: 'l5w9', type: 'word', text: 'cap', translation: '帽子', image: `https://loremflickr.com/400/400/cap,nature` },
        { id: 'l5w10', type: 'word', text: 'sausage', translation: '香肠', image: `https://loremflickr.com/400/400/sausage,nature` },
        { id: 'l5w11', type: 'word', text: 'stem', translation: '茎', image: `https://loremflickr.com/400/400/stem,nature` },
        { id: 'l5w12', type: 'word', text: 'berry', translation: '浆果', image: `https://loremflickr.com/400/400/berry,nature` },
        { id: 'l5w13', type: 'word', text: 'safe', translation: '安全的', image: `https://loremflickr.com/400/400/safe,nature` },
        { id: 'l5w14', type: 'word', text: 'cautious', translation: '谨慎的', image: `https://loremflickr.com/400/400/cautious,nature` },
        { id: 'l5w15', type: 'word', text: 'look for', translation: '寻找', image: `https://loremflickr.com/400/400/lookfor,nature` },
        { id: 'l5w16', type: 'word', text: 'rule', translation: '规则', image: `https://loremflickr.com/400/400/rule,nature` },
        { id: 'l5w17', type: 'word', text: 'summer camp', translation: '夏令营', image: `https://loremflickr.com/400/400/summercamp,nature` },
        { id: 'l5w18', type: 'word', text: 'take a break', translation: '休息', image: `https://loremflickr.com/400/400/takeabreak,nature` },
        { id: 'l5w19', type: 'word', text: 'poisonous', translation: '有毒的', image: `https://loremflickr.com/400/400/poisonous,nature` },
        { id: 'l5w20', type: 'word', text: 'throw up', translation: '呕吐', image: `https://loremflickr.com/400/400/throwup,nature` },
      ],
      qa: ['How old are you?', 'Which grade in?', 'Like sausage links?', 'How often eat them?',
        'Try stinky tofu?', 'Taste?', 'Prefer Turkey or Burger?', 'Time in nature?',
        'Enjoy school time?', 'Fun part of school?', 'Explain why?', 'What did you do yesterday?']
        .map((q, i) => ({ id: `l5q${i}`, type: 'qa' as const, text: q, referenceAnswer: 'Answer appropriately' }))
    },
    'L6': {
      words: [
        { id: 'l6w1', type: 'word', text: 'raise', translation: '举起', image: `https://loremflickr.com/400/400/raise,nature` },
        { id: 'l6w2', type: 'word', text: 'hold', translation: '举办', image: `https://loremflickr.com/400/400/hold,nature` },
        { id: 'l6w3', type: 'word', text: 'register', translation: '登记', image: `https://loremflickr.com/400/400/register,nature` },
        { id: 'l6w4', type: 'word', text: 'fundraiser', translation: '筹款活动', image: `https://loremflickr.com/400/400/fundraiser,nature` },
        { id: 'l6w5', type: 'word', text: 'occur', translation: '发生', image: `https://loremflickr.com/400/400/occur,nature` },
        { id: 'l6w6', type: 'word', text: 'bustling', translation: '繁华的', image: `https://loremflickr.com/400/400/bustling,nature` },
        { id: 'l6w7', type: 'word', text: 'baguette', translation: '法棍', image: `https://loremflickr.com/400/400/baguette,nature` },
        { id: 'l6w8', type: 'word', text: 'sculpture', translation: '雕塑', image: `https://loremflickr.com/400/400/sculpture,nature` },
        { id: 'l6w9', type: 'word', text: 'excited', translation: '兴奋的', image: `https://loremflickr.com/400/400/excited,nature` },
        { id: 'l6w10', type: 'word', text: 'disappointed', translation: '失望的', image: `https://loremflickr.com/400/400/disappointed,nature` },
        { id: 'l6w11', type: 'word', text: 'palace', translation: '宫殿', image: `https://loremflickr.com/400/400/palace,nature` },
        { id: 'l6w12', type: 'word', text: 'product', translation: '产品', image: `https://loremflickr.com/400/400/product,nature` },
        { id: 'l6w13', type: 'word', text: 'volunteer', translation: '志愿者', image: `https://loremflickr.com/400/400/volunteer,nature` },
        { id: 'l6w14', type: 'word', text: 'program', translation: '项目', image: `https://loremflickr.com/400/400/program,nature` },
        { id: 'l6w15', type: 'word', text: 'clean-up', translation: '清理', image: `https://loremflickr.com/400/400/cleanup,nature` },
        { id: 'l6w16', type: 'word', text: 'litter', translation: '垃圾', image: `https://loremflickr.com/400/400/litter,nature` },
        { id: 'l6w17', type: 'word', text: 'tryout', translation: '选拔', image: `https://loremflickr.com/400/400/tryout,nature` },
        { id: 'l6w18', type: 'word', text: 'stagehand', translation: '舞台工作人员', image: `https://loremflickr.com/400/400/stagehand,nature` },
        { id: 'l6w19', type: 'word', text: 'script', translation: '剧本', image: `https://loremflickr.com/400/400/script,nature` },
        { id: 'l6w20', type: 'word', text: 'scene', translation: '场景', image: `https://loremflickr.com/400/400/scene,nature` },
      ],
      qa: ['How old are you?', 'Which grade in?', 'Have you ever traveled?', 'Visit where?',
        'Why visit?', 'Exciting event on trip?', 'What makes excited?', 'Famous places in China?',
        'Winter clothes?', 'Fashionable design?', 'Last AD seen?', 'Family member personality.']
        .map((q, i) => ({ id: `l6q${i}`, type: 'qa' as const, text: q, referenceAnswer: 'Answer appropriately' }))
    }
  };

  const data = levelData[level] || levelData['L3'];

  return [...data.words, ...data.qa];
};

export const evaluateTest = async (
  studentName: string,
  level: Level,
  unit: string,
  audios: (Blob | null)[]
): Promise<TestResult> => {
  await new Promise(resolve => setTimeout(resolve, 3000));
  const score = Math.floor(Math.random() * 10) + 50;
  return {
    score,
    totalScore: 60,
    level,
    studentName,
    date: new Date().toLocaleDateString(),
    duration: '15分钟',
    comment: '表现得太棒了！你的发音和流利度都达到了高水平，继续加油！',
    stars: 5,
    analysis: {
      accuracy: 92,
      fluency: 88,
      vocabulary: 95,
    }
  };
};

// ============================================
// Real Backend API Functions
// ============================================

// 添加 token 到请求头
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

/**
 * 提交 Part 1 音频进行评测 (讯飞)
 */
export const submitPart1 = async (
  testId: number,
  audioBlob: Blob,
  text: string
): Promise<{
  success: boolean;
  score?: number;
  message?: string;
}> => {
  const formData = new FormData();
  formData.append('audio', audioBlob, 'part1.wav');
  formData.append('reference_text', text);

  const response = await api.post(`/tests/${testId}/part1`, formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  });
  return response.data;
};

import { FullReportResponse } from '../types';

/**
 * 上传音频到 OSS
 */
export const uploadAudio = async (
  testId: number,
  part: 'part1' | 'part2',
  audioBlob: Blob
): Promise<{ success: boolean; url: string; key: string; message: string }> => {
  const formData = new FormData();
  formData.append('test_id', testId.toString());
  formData.append('part', part);
  formData.append('audio', audioBlob, `${part}.wav`);

  const response = await api.post('/upload/audio', formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  });
  return response.data;
};

/**
 * 提交 Part 2 音频进行评测 (Qwen)
 * 1. 上传音频到 OSS
 * 2. 提交评测任务
 */
export const submitPart2 = async (
  testId: number,
  audioBlob: Blob
): Promise<{
  success: boolean;
  message?: string;
  task_id?: string;
}> => {
  try {
    // 1. 上传音频
    const uploadRes = await uploadAudio(testId, 'part2', audioBlob);
    if (!uploadRes.success || !uploadRes.url) {
      throw new Error(uploadRes.message || '音频上传失败');
    }

    // 2. 提交评测 (发送 URL)
    const response = await api.post(`/tests/${testId}/part2`, {
      audio_url: uploadRes.url
    });
    return response.data;
  } catch (error: any) {
    console.error('Part 2 提交失败:', error);
    return {
      success: false,
      message: error.response?.data?.detail?.message || error.message || '提交失败'
    };
  }
};

/**
 * 获取完整测评报告
 */
export const getTestReport = async (testId: number): Promise<FullReportResponse> => {
  const response = await api.get(`/tests/${testId}/report`);
  return response.data;
};

