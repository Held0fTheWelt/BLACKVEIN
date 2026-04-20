/**
 * Test suite for escapeHtml() function in manage_users.js
 * Verifies that XSS payloads are properly neutralized
 */

// Copy of the escapeHtml function from manage_users.js
function escapeHtml(text) {
    if (!text) return "";
    return String(text)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#39;");
}

// XSS Payload Test Suite
const xssPayloads = [
    {
        name: "Script tag injection",
        payload: "<script>alert('XSS')</script>",
        description: "Classic script tag payload"
    },
    {
        name: "Event handler - onload",
        payload: "\" onload=\"alert('XSS')\"",
        description: "Attribute injection with event handler"
    },
    {
        name: "Event handler - onerror",
        payload: "'\"><img src=x onerror=alert('XSS')>",
        description: "Image tag with onerror handler"
    },
    {
        name: "Script in src attribute",
        payload: "javascript:alert('XSS')",
        description: "Protocol-based XSS in src"
    },
    {
        name: "SVG with onload",
        payload: "<svg onload=alert('XSS')>",
        description: "SVG element with event handler"
    },
    {
        name: "HTML entity bypass attempt",
        payload: "&lt;script&gt;alert('XSS')&lt;/script&gt;",
        description: "Double encoding attempt"
    },
    {
        name: "Mixed quotes and angle brackets",
        payload: "' OR '1'='1",
        description: "Quote-based injection (SQL-style, in HTML context)"
    },
    {
        name: "Iframe injection",
        payload: "<iframe src='javascript:alert(\"XSS\")'>",
        description: "Iframe with JavaScript protocol"
    },
    {
        name: "Data URI with script",
        payload: "data:text/html,<script>alert('XSS')</script>",
        description: "Data URI payload"
    },
    {
        name: "Complex HTML tag",
        payload: "<input type=\"text\" value=\"\" onclick=\"alert('XSS')\" />",
        description: "Input tag with onclick handler"
    },
    {
        name: "Angle brackets only",
        payload: "<>",
        description: "Simple angle brackets"
    },
    {
        name: "Ampersand entity",
        payload: "&",
        description: "Ampersand character"
    },
    {
        name: "Quotes",
        payload: "\"' ",
        description: "Mixed quotes"
    },
    {
        name: "Username with HTML",
        payload: "admin<script>alert('XSS')</script>",
        description: "Realistic user input with payload"
    },
    {
        name: "Email with HTML",
        payload: "user@example.com\"><script>alert('XSS')</script>",
        description: "Email-like input with HTML injection"
    }
];

// Test helper function
function testPayload(payload) {
    const escaped = escapeHtml(payload);

    // Verify that the escaped output doesn't contain unescaped dangerous characters
    const hasUnescapedScript = escaped.includes('<script') || escaped.includes('</script>');
    const hasUnescapedEvent = /on\w+\s*=/.test(escaped);
    const hasUnescapedTag = /<[^&][^>]*>/.test(escaped);

    return {
        payload,
        escaped,
        isSafe: !hasUnescapedScript && !hasUnescapedEvent && !hasUnescapedTag
    };
}

// Run all tests
console.log("=".repeat(80));
console.log("XSS Payload Testing Suite for escapeHtml()");
console.log("=".repeat(80));

let passCount = 0;
let failCount = 0;

xssPayloads.forEach((test, index) => {
    const result = testPayload(test.payload);

    if (result.isSafe) {
        passCount++;
        console.log(`\n[PASS] Test ${index + 1}: ${test.name}`);
    } else {
        failCount++;
        console.log(`\n[FAIL] Test ${index + 1}: ${test.name}`);
    }

    console.log(`Description: ${test.description}`);
    console.log(`Original:    ${result.payload}`);
    console.log(`Escaped:     ${result.escaped}`);
    console.log(`Safe:        ${result.isSafe ? 'YES' : 'NO'}`);
});

console.log("\n" + "=".repeat(80));
console.log("TEST SUMMARY");
console.log("=".repeat(80));
console.log(`Total Tests: ${xssPayloads.length}`);
console.log(`Passed:      ${passCount}`);
console.log(`Failed:      ${failCount}`);
console.log(`Result:      ${failCount === 0 ? 'ALL TESTS PASSED ✓' : 'SOME TESTS FAILED ✗'}`);
console.log("=".repeat(80));

// Export for use in Node.js or browser environments
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { escapeHtml, testPayload, xssPayloads };
}
