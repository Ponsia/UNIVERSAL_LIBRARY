#!/bin/bash
find ~/snap/flutter -type f -name "build.gradle*" -exec grep -H "25.0.3" {} + 2>/dev/null
find ~/.pub-cache -type f -name "build.gradle*" -exec grep -H "25.0.3" {} + 2>/dev/null
