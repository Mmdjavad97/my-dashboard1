import test from 'node:test';
import assert from 'node:assert/strict';
import {solarDate,solarValue} from '../frontend/src/dates.js';
import {MEETING_DEFAULTS,blankMeeting,meetingDraft,meetingNeedsDefaults} from '../frontend/src/meeting-defaults.js';
test('Solar Hijri generation excludes era and follows Tehran midnight',()=>{
 assert.equal(solarDate(new Date('2026-11-10T10:00:00Z')),'1405/08/19');
 assert.equal(solarDate(new Date('2026-11-09T22:00:00Z')),'1405/08/19');
 assert.equal(solarDate(new Date('2026-11-09T22:00:00Z'),'UTC'),'1405/08/18');
 assert.match(solarDate(),/^\d{4}\/\d{2}\/\d{2}$/);
});
test('Legacy AP suffixes, Persian digits and Gregorian dates normalize without a suffix',()=>{
 assert.equal(solarValue('1405/08/19 AP'),'1405/08/19');
 assert.equal(solarValue('۱۴۰۵/۰۸/۱۹\u200f AP'),'1405/08/19');
 assert.equal(solarValue('2026-11-10 AP'),'1405/08/19');
 assert.equal(solarValue('1405/08/19'),'1405/08/19');
});
test('All eleven new agendas have independent Not Raised/Not Started defaults',()=>{
 const rows=blankMeeting();assert.equal(rows.length,11);
 assert.ok(rows.every(r=>r[3]==='Not Raised'&&r[5]==='Not Started'));
 assert.equal(meetingNeedsDefaults(rows),false);
 rows[0][3]='Raised';assert.equal(rows[1][3],MEETING_DEFAULTS.discussion);
});
test('Missing statuses get defaults without resetting saved choices or mutating source',()=>{
 const original=[['Topic','Title','Owner','Raised','Note','Done'],['','','','Not Raised','','In Progress'],['','','','','','']];
 const before=structuredClone(original);const draft=meetingDraft(original);
 assert.deepEqual(original,before);
 assert.equal(draft[0][3],'Raised');assert.equal(draft[0][5],'Done');
 assert.equal(draft[1][5],'In Progress');assert.equal(draft[2][3],'Not Raised');assert.equal(draft[2][5],'Not Started');
 assert.equal(draft.length,11);assert.equal(meetingNeedsDefaults(original),true);
});
