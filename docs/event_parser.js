function parseEvent(event_str) {
    let event = {}
    
    let lines = event_str.split('\n')
    
    for (var i = 0; i < lines.length; i++) {
        let line = lines[i]
        let idx = line.indexOf(':')
        if (idx < 0) {
            break
        }
        let prop = line.slice(0, idx);
        let value = line.slice(idx+1, line.length);
        
        if (prop == 'tags') {
            value = value.split(',').filter( t => { return t; });
        }
        
        event[prop] = value
    }
    if (i < lines.length) {
        event.content = lines.slice(i, lines.length).join('\n')
    }
    
    return event
}

function serializeEvent(event) {
    let event_str = ''
    let guaranteed = ['id', 'timestamp', 'source', 'tags']
    for (var i = 0; prop = guaranteed[i]; i++) {
        let value = event[prop];
        if (prop == 'tags') {
            value = value.join(',');
        }
        event_str += prop + ':' + value + '\n';
    }
    
    for (var prop in event) {  // add custom headers
        if (!guaranteed.includes(prop) && prop != 'content') {
            event_str += prop + ':' + event[prop] + '\n';
        }
    }
    
    event_str += event.content;
    return event_str
}


var event_str = ['id:331c531d-6eb4-4fb5-84d3-ea6937b01fdd',
                 'timestamp: 1509989630.6749051',
                 'source:/dev/sensors/door1-sensor',
                 'tags:sensors,home,doors,door1',
                 'x-header:somevalue',
                 'Door has been unlocked.'].join('\n')

var event = parseEvent(event_str);
console.log(event)
// prints: 
// { id: '331c531d-6eb4-4fb5-84d3-ea6937b01fdd',
//  timestamp: ' 1509989630.6749051',
//  source: '/dev/sensors/door1-sensor',
//  tags: [ 'sensors', 'home', 'doors', 'door1' ],
//  'x-header': 'somevalue',
//  content: 'Door has been unlocked.' }


var serialized = serializeEvent(event);
console.log(serialized);
// prints:
// id:331c531d-6eb4-4fb5-84d3-ea6937b01fdd
// timestamp: 1509989630.6749051
// source:/dev/sensors/door1-sensor
// tags:sensors,home,doors,door1
// x-header:somevalue
// Door has been unlocked.


