import '../css/main.css';
import htmx from 'htmx.org';
import Alpine from 'alpinejs'
import { sayHello } from './important.js';
 
window.htmx = htmx;
window.Alpine = Alpine
Alpine.start()

console.log("Main JavaScript file loaded.");
sayHello('William');