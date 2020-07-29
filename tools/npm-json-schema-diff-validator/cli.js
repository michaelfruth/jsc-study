const difftool = require('json-schema-diff-validator')
const path = require("path");

async function check(json1, json2) {
    const start = Date.now() / 1000
    try {
        difftool.validateSchemaCompatibility(json1, json2, {allowNewEnumValue: false})
        console.log("OK")
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

// Remove the schema tag so npm-is-json-schema-subset will handle all schemas.
json1.$schema = null
json2.$schema = null
check(json1, json2)