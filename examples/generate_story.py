"""Regenerate the entirely fictional, multi-month report acceptance export."""
import json
from datetime import datetime,timedelta
from pathlib import Path

names=['Alice','Sam','Rahul','Mia'];messages=[]
def add(time,name,text,reply=None,photo=False,reactions=False):
    index=len(messages)+1
    item={'id':index,'type':'message','date':time.isoformat(),'from':name,'from_id':'user'+str(names.index(name)+1),'text':text}
    if reply:item['reply_to_message_id']=reply
    if photo:item['photo']=f'photos/fictional-{index}.jpg'
    if reactions:item['reactions']=[{'emoji':'❤','count':1,'recent':[{'from_id':'user3'}]}]
    messages.append(item);return index

for day in range(181):
    date=datetime(2026,1,1)+timedelta(days=day)
    if date.month==5 and 8<=date.day<=22:continue
    topic='reading corner' if date.month<=2 else 'movie night' if date.month<=4 else 'garden party'
    r=add(date.replace(hour=7), 'Rahul', 'Good morning!')
    if day%2==0:add(date.replace(hour=7,minute=2),'Rahul',f'Any plans for {topic}? Who can help?')
    s=add(date.replace(hour=7,minute=4),'Sam',f'Here is a useful link https://example.com/{topic.replace(" ","-")}',r)
    if date.month<5:
        a=add(date.replace(hour=7,minute=6),'Alice',f'I have been thinking about our {topic}. We could start with a small plan, invite everyone to contribute, and leave time for a quiet break. The details matter: let us bring snacks, check the space, and make sure the whole group can enjoy it. What do you think?',s)
        add(date.replace(hour=7,minute=7),'Sam','Looks good to me.',a)
    add(date.replace(hour=7,minute=9),'Mia','Yep 🌿',s,reactions=True)
    if day%3==0:
        for offset,line in enumerate(['Quick update','The supplies arrived','I checked the list','Everything is ready']):add(date.replace(hour=12,minute=offset//2,second=(offset%2)*20),'Sam',line)
    if date.weekday()>=5:
        prev=None
        for i in range(18 if date.month!=5 else 5):
            name=names[i%4];text=(f'For the {topic}, I can bring a few extra supplies and prepare the space. Looking forward to making something together.' if name=='Alice' else 'Lovely 😄' if name=='Mia' else f'Can we confirm the plan for {topic}?' if name=='Rahul' else f'Another idea: https://example.com/ideas/{day}')
            prev=add(date.replace(hour=17,minute=i*2),name,text,prev,photo=name=='Mia' and i%8==3,reactions=name=='Mia')
    if date.month>=3 and date.month!=5 and day%3!=0:
        prev=None
        for i in range(10):
            name='Mia' if i%2==0 else 'Sam'
            prev=add(date.replace(hour=23,minute=5+i*4),name,'Movie night forever 🎬' if name=='Mia' else 'One more recommendation for movie night!',prev,reactions=name=='Mia')

messages.sort(key=lambda m:m['date'])
path=Path(__file__).with_name('telegram_story_group.json')
path.write_text(json.dumps({'id':777,'name':'The After-Hours Club (fictional)','type':'private_supergroup','messages':messages},ensure_ascii=False,indent=2)+'\n')
print(f'Generated {len(messages)} fictional messages in {path.name}')
