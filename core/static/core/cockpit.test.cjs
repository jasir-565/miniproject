const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');

function environment() {
    let starts = 0, stops = 0, deliver;
    const document = {
        createElement(tag) { return { tag, textContent: '', children: [], append(...children) { this.children.push(...children); } }; },
        createTextNode(text) { return { textContent: text }; },
        addEventListener() {},
    };
    const context = { document, window: {}, navigator: { geolocation: {
        watchPosition(success) { starts++; deliver = success; return 123; },
        clearWatch(id) { assert.equal(id, 123); stops++; },
    } } };
    context.window = context;
    vm.runInNewContext(fs.readFileSync(__dirname + '/cockpit.js', 'utf8'), context);
    return { api: context.AutoNexa, starts: () => starts, stops: () => stops, deliver: value => deliver(value) };
}

test('popup keeps markup and quotes as text nodes', () => {
    const { api } = environment();
    const attack = '<img src=x onerror=alert(1)>';
    const popup = api.popup("Owner's car", attack);
    assert.equal(popup.children[0].textContent, "Owner's car");
    assert.equal(popup.children[2].textContent, attack);
    assert.equal(popup.innerHTML, undefined);
});

test('coordinates accept zero and reject absent or invalid values', () => {
    const { api } = environment();
    assert.equal(api.hasCoordinates(0, 0), true);
    for (const [lat, lng] of [[null, 1], ['', 1], [NaN, 1], [Infinity, 1], [91, 1], [0, -181]]) {
        assert.equal(api.hasCoordinates(lat, lng), false);
    }
});

test('request cards share one GPS watcher and unsubscribe independently', () => {
    const env = environment();
    let first = 0, second = 0;
    const stopFirst = env.api.watchGPS(() => first++, () => {});
    const stopSecond = env.api.watchGPS(() => second++, () => {});
    assert.equal(env.starts(), 1);
    env.deliver({ coords: { latitude: 0, longitude: 0 } });
    assert.equal(first, 1);
    assert.equal(second, 1);
    stopFirst();
    env.deliver({ coords: { latitude: 1, longitude: 1 } });
    assert.equal(first, 1);
    assert.equal(second, 2);
    assert.equal(env.stops(), 0);
    stopSecond();
    assert.equal(env.stops(), 1);
});
