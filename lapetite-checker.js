/*
 To run on the command line:
   $ phantomjs lapetite-checker.js

 Sample curl commands:

 curl -v -c ~/tmp/lapetite.cookie https://www.iclassprov2.com/parentportal/lapetite/location/change?locationId=2
 curl -o ~/tmp/lapetite.html -b ~/tmp/lapetite.cookie 'https://www.iclassprov2.com/parentportal/lapetite/classes?day=7&level=14&filters=Submit'
 */

"use strict";
var system = require('system');
var fs = require('fs');
phantom.cookiesEnabled = true;

try {
  var settings = JSON.parse(fs.read('config.json'));
  settings.earliestTime = normalizeTime(settings.earliestTime);
  settings.latestTime = normalizeTime(settings.latestTime);
}
catch(e) {
  console.log('Could not find config.json');
  console.log(e);
  phantom.exit();
}

var locationPage = require('webpage').create();
locationPage.onLoadFinished = function(status) {
  if (status === 'success') {
    openListingPage();
  }
};

locationPage.open('https://www.iclassprov2.com/parentportal/lapetite/location/change?locationId=' + settings.location);

function openListingPage() {
  var listingPage = require('webpage').create();

  listingPage.onConsoleMessage = function(msg) {
    console.log(msg);
  };

  listingPage.onLoadFinished = function(status) {
    var listings = listingPage.evaluate(getListings);
    for (var i = 0; i < listings.length; i++) {
      var listing = listings[i];

      if (settings.verbose) {
        console.log(listing.status);
      } else {
        if (listing.status === "OPEN" &&
            (inTimeWindow(listing.startTime, settings.earliestTime, settings.latestTime))) {
          console.log(listing.name);
        }
      }
    }

    phantom.exit(0);
  };
  listingPage.open('https://www.iclassprov2.com/parentportal/lapetite/classes?day=' +
                   settings.day +
                   '&level=' + settings.level +
                   '&filters=Submit');
}

/**
 * Return an object of class_name -> availability
 */
function getListings() {
  var result = [];
  var classEntries = document.getElementsByClassName("class");
  for (var i = 0; i < classEntries.length; i++) {
    var listing = {}; // individual listing with name, availability, and start time
    var entry = classEntries[i];
    listing.name = entry.querySelector(".class_name").innerText;
    listing.status = entry.querySelector(".availability").innerText;
    listing.startTime = entry.querySelector('.class_schedule tbody').rows[0].cells[1].innerText;

    result.push(listing);
  };

  return result;
}

/**
 * Reformat a time in '00:00am' format to '00:00 am'
 */
function normalizeTime(timeStr) {
  var timeRegex = /(\d+:\d+)\s*([AaPp][Mm])/;
  if (timeRegex.test(timeStr)) {
    return timeStr.replace(timeRegex, '$1 $2');
  } else {
    throw "bad time: " + timeStr;
  }
}

function inTimeWindow(testTime, startTime, endTime) {
  var testDate = dummyDate(testTime);
  var startDate = dummyDate(startTime);
  var endDate = dummyDate(endTime);

  if (endDate - startDate < 0) throw "bad time settings";
  if (testDate - startDate < 0) return false;
  if (endDate - testDate < 0) return false;
  return true;
}

function dummyDate(time) {
  var DUMMY_DATE = "1/1/2001";
  return Date.parse(DUMMY_DATE + ' ' + normalizeTime(time));
}
