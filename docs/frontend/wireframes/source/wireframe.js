const pages = [
  ['home','Главная','Начните с безопасного пути от установки до dry-run.',['Что такое crypt','Маршрут запуска','Разделы документации'],['hero','diagram','cards']],
  ['quick-start','Быстрый старт','Установите crypt, подготовьте данные, запустите бэктест и безопасный dry-run.',['Установка','Данные','Бэктест','Dry-run'],['steps','code','callout','diagram']],
  ['overview','Что такое crypt','Исследовательский workbench, точный replay и owner-controlled execution в одной системе.',['Границы системы','Что входит','Что не входит'],['diagram','cards','callout']],
  ['architecture','Архитектура','Проследите путь данных и решений от OKX или Parquet до артефактов и исполнения.',['Карта системы','Поток данных','Источники истины','Отказы'],['diagram','callout','table']],
  ['data','Данные','Подготовьте закрытые свечи и проверьте полноту локального Parquet-хранилища.',['Источники','Таймфреймы','Backfill','Ошибки данных'],['diagram','table','code','callout']],
  ['strategies','Стратегии','Разберите конфигурацию, registry, signals и границу execution context.',['Контракт стратегии','Конфигурация','Registry','Расширение'],['code','diagram','cards','callout']],
  ['backtester','Бэктестер','Запустите точный replay и поймите warmup, accounting и набор артефактов.',['Модель replay','Команда run','Границы времени','Артефакты'],['diagram','code','table','callout']],
  ['research','Исследования','Выберите optimize или DSS и поймите механику без публикации результатов.',['Выбор workflow','Optimize','DSS','Ограничения'],['cards','code','diagram','callout']],
  ['live-execution','Live execution','Разберите dry-run, H1 scheduling, OKX sync, safety и recovery.',['Режимы','Синхронизация','Orders и fills','Railway','Recovery'],['cards','diagram','callout','code','table']],
  ['cli','CLI','Найдите поддерживаемую команду, флаг, default и точный пример.',['Индекс команд','Backtester','Runtime и data','Flags'],['code','table','cards']],
  ['configuration','Конфигурация','Найдите setting, default, эффект и границу риска.',['Приоритет','Base settings','Execution','Railway'],['cards','table','code','callout']],
  ['development','Разработка и тестирование','Найдите модуль и проверьте изменение поддерживаемыми командами.',['Структура','Workflow','Проверки','Расширение'],['diagram','code','table']],
  ['troubleshooting','Решение проблем','Сопоставьте симптом с причиной, безопасным восстановлением и проверкой.',['Установка','Данные','Backtester','OKX и sync','Railway'],['cards','callout','code','table']],
];
const params=new URLSearchParams(location.search); const id=params.get('screen')||'home';
const page=pages.find(p=>p[0]===id)||pages[0];
document.title=`${page[1]} — crypt wireframe`; document.querySelector('#title').textContent=page[1];
document.querySelector('#lead').textContent=page[2]; document.querySelector('#crumb').textContent=`crypt docs / ${page[1]}`;
document.querySelector('#viewport').textContent=`${innerWidth}×${innerHeight}`;
document.querySelector('#character').textContent=id==='live-execution'?'[ LIVE OPERATOR — safety guidance ]':id==='backtester'?'[ BACKTESTER ROBOT — replay guidance ]':'[ RESEARCHER / WORKSHOP GUIDE — contextual illustration ]';
const nav=document.querySelector('#navigation'); pages.forEach(p=>{const a=document.createElement('a');a.href=`?screen=${p[0]}`;a.textContent=p[1];if(p[0]===id)a.className='active';nav.append(a)});
const toc=document.querySelector('#toc'); page[3].forEach((x,i)=>{const a=document.createElement('a');a.href=`#s${i}`;a.textContent=x;toc.append(a)});
const blocks=document.querySelector('#blocks');
function body(type){if(type==='diagram')return '<div class="diagram"><div class="node">Источник</div><div class="node">Контракт</div><div class="node">Решение</div><div class="node">Результат</div></div>';if(type==='code')return '<div class="code"><button class="copy">Копировать</button>$ PYTHONPATH=src uv run …<br><br># command and configuration contract</div>';if(type==='callout')return '<div class="callout"><b>Важно</b><br>Граница безопасности, источник истины и точный следующий шаг.</div>';if(type==='cards')return '<div class="cards"><div class="card">Ключевой блок A</div><div class="card">Ключевой блок B</div><div class="card">Ключевой блок C</div></div>';if(type==='table')return '<div class="table"><div><b>Имя</b><b>Назначение</b><b>Состояние</b></div><div><span>contract</span><span>source-backed</span><span>active</span></div><div><span>fallback</span><span>recovery</span><span>blocked</span></div></div>';return '<div class="rows"><div class="row"></div><div class="row mid"></div><div class="row short"></div></div>'}
page[4].forEach((type,i)=>{const s=document.createElement('section');s.className='block';s.id=`s${i}`;s.innerHTML=`<h2>${page[3][i]||'Следующий шаг'}</h2>${body(type)}`;blocks.append(s)});
addEventListener('resize',()=>document.querySelector('#viewport').textContent=`${innerWidth}×${innerHeight}`);
