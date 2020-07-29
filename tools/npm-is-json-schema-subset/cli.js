import isJsonSchemaSubset from 'is-json-schema-subset';

const path = require("path");

async function check(json1, json2) {
    const start = Date.now() / 1000
    try {
        if (await isJsonSchemaSubset(json1, json2)) {
            console.log('OK');
        } else {
            console.log('Fail');
        }
    } catch (e) {
        console.log("Exception")
        console.log(e.toString())
    } finally {
        const end = Date.now() / 1000

        console.log(start)
        console.log(end)
    }

}

const absolutePath1 = path.resolve(process.argv[2]);
const absolutePath2 = path.resolve(process.argv[3]);

const fs = require('fs')
var json1, json2;
try {
    json1 = require(absolutePath1)
} catch (e) {
    json1 = fs.readFileSync(absolutePath1)
}
try {
    json2 = require(absolutePath2)
} catch (e) {
    json2 = fs.readFileSync(absolutePath2)
}

// Remove drafts because only schmeas having Draft5 or above will be accepted.
json1.$schema = null
json2.$schema = null

// Remove the schema tag so npm-is-json-schema-subset will handle all schemas.
check(json1, json2)