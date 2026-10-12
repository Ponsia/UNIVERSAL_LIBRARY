import re

with open('lib/services/rag_service.dart', 'r') as f:
    content = f.read()

content = content.replace("KnowledgeBase.chemistryChunks", "KnowledgeBase.allChunks")

greet_replacement = """    if (lowerQuery.contains("hello") || lowerQuery.contains("hi") || lowerQuery.contains("mambo") || lowerQuery.contains("habari")) {
      return "Hello! Mimi ni UniLib AI, msaidizi wako wa masomo. Nimejifunza vitabu vya Chemistry, Biology na Physics vya TIE. Niulize swali lolote la kitaaluma!";
    }

    // 1. Retrieve Phase
    List<String> contextChunks = await _retrieveRelevantChunks(query);
    
    // 2. Generate Phase
    if (contextChunks.isNotEmpty) {
      String mainContext = contextChunks.first;
      String response = "Kulingana na vitabu vya TIE:\n\n$mainContext";
      
      if (contextChunks.length > 1 && contextChunks[1].length > 20) {
        response += "\n\nPia, ${contextChunks[1].replaceFirst(contextChunks[1][0], contextChunks[1][0].toLowerCase())}";
      }
      return response;
    } else {
      return "Sijapata jibu la moja kwa moja kutoka kwenye database yangu ya vitabu (Biology, Chemistry, Physics). Hata hivyo, kama msaidizi wa kitaaluma, naweza kukusaidia kujibu swali lako. Unaweza kufafanua zaidi swali lako?";
    }"""

content = re.sub(r"    if \(lowerQuery == \"hello\".*?different chemistry topic\?\";\n    \}", greet_replacement, content, flags=re.DOTALL)

with open('lib/services/rag_service.dart', 'w') as f:
    f.write(content)
