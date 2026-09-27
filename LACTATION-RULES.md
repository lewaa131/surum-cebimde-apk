# Sağım sınıflaması — 0.13.5

Gerçek doğum kaydı, bağlı buzağı, kullanıcının sağım seçimi ve “hiç doğurmadı” bilgisi yaş tahmininden önceliklidir. Kuru ve sağılmıyor durumları korunur.

Geçmişi bilinmeyen aktif dişilerde:

- 24 ay dolmadan sağmal tahmini yapılmaz.
- Kayıtlı en erken tohumlama 24 aylık olduğu gün veya öncesindeyse ilk doğum koruması uygulanır. Hayvan yaşlansa, kontrol sonucu olumsuz olsa veya tahmini doğum günü geçse bile bu koruma doğum onayı gelmeden kalkmaz.
- Bu genç tohumlama kaydı bulunmayan 24 ay ve üzeri dişiler sağmal toplamına “tahmini” olarak girer. Geçmiş bir doğum tarihi veya buzağı kaydı uydurulmaz.
- Not veya tohumlama düzenlemek tahmini kesin doğum bilgisine dönüştürmez. Gerçek doğum kaydı normal döngüyü başlatır.

13–15 ay ilk tohumlama ve 22–24 ay ilk doğum yetiştirme hedefleridir; her hayvanın gerçekleşen doğumunu kanıtlamaz. 24 ay, yazılımda ihtiyatlı bir ayırma sınırıdır. Çok geç ilk tohumlaması yapılan ve geçmişi bilinmeyen düvelerde tahmin yine yanılabilir. Mevcut “Düve” seçimi bu durumda tahmini kapatır; “Sağım durumu” gerçek durumun kaydedilmesini sağlar.

Kaynaklar:
- https://extension.psu.edu/dairy-heifer-production
- https://www.msdvetmanual.com/management-and-nutrition/nutrition-dairy-cattle/feeding-dairy-calves-from-weaning-through-maturation
