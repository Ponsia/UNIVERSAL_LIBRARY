import 'package:dio/dio.dart';
import 'package:flutter/foundation.dart';

class SmsService {
  static const String apiKey = "";
  static const String senderId = "MESEJI";
  static const String hfToken = "";

  /// Cleans the phone number to standard Tanzania format (255XXXXXXXXX)
  static String formatPhoneNumber(String phone) {
    String cleaned = phone.replaceAll(RegExp(r'[^\d]'), '');
    if (cleaned.startsWith('0')) {
      cleaned = '255${cleaned.substring(1)}';
    } else if (cleaned.startsWith('+255')) {
      cleaned = cleaned.substring(1);
    } else if (!cleaned.startsWith('255') && cleaned.length == 9) {
      cleaned = '255$cleaned';
    }
    return cleaned;
  }

  /// Sends the Hugging Face access token via SMS to the student's phone number
  static Future<bool> sendTokenSms(String phone, String username) async {
    final formattedPhone = formatPhoneNumber(phone);
    final message = "Hongera na karibu Universal Library, $username! Your offline study model access token is: $hfToken . Karibu ujisomee bila internet.";

    final dio = Dio(
      BaseOptions(
        connectTimeout: const Duration(seconds: 15),
        receiveTimeout: const Duration(seconds: 15),
        headers: {
          'x-api-key': apiKey,
          'Content-Type': 'application/json',
          'Accept': 'application/json',
        },
      ),
    );

    try {
      final response = await dio.post(
        'https://meseji.co.tz/api/v1/sms/send',
        data: {
          'contacts': formattedPhone,
          'message': message,
          'sender_id': senderId,
        },
      );
      debugPrint("SMS response: ${response.statusCode} - ${response.data}");
      if (response.statusCode == 200 || response.statusCode == 201) {
        final data = response.data;
        if (data is Map && (data['status'] == 'success' || data['batch_id'] != null)) {
          return true;
        }
        return true;
      }
      return false;
    } catch (e) {
      debugPrint("SMS delivery error: $e");
      // Even if network SMS fails or gateway error, return false so UI can show backup
      return false;
    }
  }
}

