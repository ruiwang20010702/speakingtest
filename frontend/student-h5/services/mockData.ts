import { Question, Level } from '../types';

// 模拟题目数据
export const mockQuestions: Record<string, Question[]> = {
  'L0-Full Level': [
    // Part 1: 词汇朗读 (20题)
    { id: '1', type: 'word', text: 'apple', translation: '苹果', image: '/Word picture/apple.png', referenceAnswer: 'apple' },
    { id: '2', type: 'word', text: 'banana', translation: '香蕉', image: '/Word picture/banana.png', referenceAnswer: 'banana' },
    { id: '3', type: 'word', text: 'cat', translation: '猫', image: '/Word picture/cat.png', referenceAnswer: 'cat' },
    { id: '4', type: 'word', text: 'dog', translation: '狗', image: '/Word picture/dog.png', referenceAnswer: 'dog' },
    { id: '5', type: 'word', text: 'elephant', translation: '大象', image: '/Word picture/elephant.png', referenceAnswer: 'elephant' },
    { id: '6', type: 'word', text: 'fish', translation: '鱼', image: '/Word picture/fish.png', referenceAnswer: 'fish' },
    { id: '7', type: 'word', text: 'giraffe', translation: '长颈鹿', image: '/Word picture/giraffe.png', referenceAnswer: 'giraffe' },
    { id: '8', type: 'word', text: 'horse', translation: '马', image: '/Word picture/horse.png', referenceAnswer: 'horse' },
    { id: '9', type: 'word', text: 'ice cream', translation: '冰淇淋', image: '/Word picture/icecream.png', referenceAnswer: 'ice cream' },
    { id: '10', type: 'word', text: 'juice', translation: '果汁', image: '/Word picture/juice.png', referenceAnswer: 'juice' },
    { id: '11', type: 'word', text: 'kite', translation: '风筝', image: '/Word picture/kite.png', referenceAnswer: 'kite' },
    { id: '12', type: 'word', text: 'lion', translation: '狮子', image: '/Word picture/lion.png', referenceAnswer: 'lion' },
    { id: '13', type: 'word', text: 'monkey', translation: '猴子', image: '/Word picture/monkey.png', referenceAnswer: 'monkey' },
    { id: '14', type: 'word', text: 'nose', translation: '鼻子', image: '/Word picture/nose.png', referenceAnswer: 'nose' },
    { id: '15', type: 'word', text: 'orange', translation: '橙子', image: '/Word picture/orange.png', referenceAnswer: 'orange' },
    { id: '16', type: 'word', text: 'panda', translation: '熊猫', image: '/Word picture/panda.png', referenceAnswer: 'panda' },
    { id: '17', type: 'word', text: 'queen', translation: '女王', image: '/Word picture/queen.png', referenceAnswer: 'queen' },
    { id: '18', type: 'word', text: 'rabbit', translation: '兔子', image: '/Word picture/rabbit.png', referenceAnswer: 'rabbit' },
    { id: '19', type: 'word', text: 'sun', translation: '太阳', image: '/Word picture/sun.png', referenceAnswer: 'sun' },
    { id: '20', type: 'word', text: 'tiger', translation: '老虎', image: '/Word picture/tiger.png', referenceAnswer: 'tiger' },
    // Part 2: 对话问答 (12题)
    { id: '21', type: 'qa', text: 'What is your name?', translation: '你叫什么名字？', image: '', referenceAnswer: 'My name is...' },
    { id: '22', type: 'qa', text: 'How old are you?', translation: '你几岁了？', image: '', referenceAnswer: 'I am... years old.' },
    { id: '23', type: 'qa', text: 'What color do you like?', translation: '你喜欢什么颜色？', image: '', referenceAnswer: 'I like...' },
    { id: '24', type: 'qa', text: 'Do you like apples?', translation: '你喜欢苹果吗？', image: '', referenceAnswer: 'Yes, I do. / No, I don\'t.' },
    { id: '25', type: 'qa', text: 'What can you see?', translation: '你能看到什么？', image: '', referenceAnswer: 'I can see...' },
    { id: '26', type: 'qa', text: 'How many apples are there?', translation: '有多少个苹果？', image: '', referenceAnswer: 'There are... apples.' },
    { id: '27', type: 'qa', text: 'What is this?', translation: '这是什么？', image: '', referenceAnswer: 'This is a/an...' },
    { id: '28', type: 'qa', text: 'Where is the cat?', translation: '猫在哪里？', image: '', referenceAnswer: 'The cat is...' },
    { id: '29', type: 'qa', text: 'What do you do in the morning?', translation: '你早上做什么？', image: '', referenceAnswer: 'I... in the morning.' },
    { id: '30', type: 'qa', text: 'Can you swim?', translation: '你会游泳吗？', image: '', referenceAnswer: 'Yes, I can. / No, I can\'t.' },
    { id: '31', type: 'qa', text: 'What is your favorite animal?', translation: '你最喜欢的动物是什么？', image: '', referenceAnswer: 'My favorite animal is...' },
    { id: '32', type: 'qa', text: 'What do you want to be?', translation: '你想成为什么？', image: '', referenceAnswer: 'I want to be a/an...' },
  ],
  'L1-Unit 1-4': [
    // 类似的模拟数据，可以根据需要添加
    ...Array.from({ length: 20 }, (_, i) => ({
      id: `L1-1-${i + 1}`,
      type: 'word' as const,
      text: `word${i + 1}`,
      translation: `单词${i + 1}`,
      image: `/Word picture/word${i + 1}.png`,
      referenceAnswer: `word${i + 1}`
    })),
    ...Array.from({ length: 12 }, (_, i) => ({
      id: `L1-2-${i + 1}`,
      type: 'qa' as const,
      text: `Question ${i + 1}?`,
      translation: `问题${i + 1}？`,
      image: '',
      referenceAnswer: `Answer ${i + 1}`
    }))
  ],
  'L2-Unit 1-4': [
    ...Array.from({ length: 20 }, (_, i) => ({
      id: `L2-1-${i + 1}`,
      type: 'word' as const,
      text: `word${i + 1}`,
      translation: `单词${i + 1}`,
      image: `/Word picture/word${i + 1}.png`,
      referenceAnswer: `word${i + 1}`
    })),
    ...Array.from({ length: 12 }, (_, i) => ({
      id: `L2-2-${i + 1}`,
      type: 'qa' as const,
      text: `Question ${i + 1}?`,
      translation: `问题${i + 1}？`,
      image: '',
      referenceAnswer: `Answer ${i + 1}`
    }))
  ]
};

// 获取模拟数据的 key
function getMockKey(level: Level, unit: string): string {
  return `${level}-${unit}`;
}

// 检查是否应该使用模拟数据（开发模式）
export function shouldUseMockData(): boolean {
  // 检查环境变量或 localStorage 标志
  return localStorage.getItem('USE_MOCK_DATA') === 'true' || 
         import.meta.env.DEV && !import.meta.env.VITE_API_URL;
}

// 获取模拟题目
export function getMockQuestions(level: Level, unit: string): Question[] {
  const key = getMockKey(level, unit);
  return mockQuestions[key] || mockQuestions['L0-Full Level'];
}

// 模拟报告数据
export const mockReport = {
  part1_score: 85,
  part2_score: 78,
  total_score: 82,
  star_level: 4,
  part2_suggestions: [
    '建议多练习日常对话，提高流利度',
    '注意单词发音的准确性',
    '可以尝试用更完整的句子回答问题'
  ]
};

