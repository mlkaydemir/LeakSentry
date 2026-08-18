# 🛡️ LeakSentry

> **k-Anonymity** matematiksel gizlilik modeli ve **Have I Been Pwned (HIBP)** API'si kullanarak yerel parola sızıntı kontrolü yapan modern CLI güvenlik aracı.

---

## 📌 Proje Hakkında

**LeakSentry**, girdiğiniz parolaların geçmiş veri ihlallerinde (*data breaches*) yer alıp almadığını kontrol eden hafif, interaktif ve güvenli bir komut satırı aracıdır. 

Geleneksel araçların aksine parolayı hiçbir zaman düz metin (*plaintext*) veya tam hash olarak internete iletmez; **sıfır bilgi (*zero-knowledge*)** prensibiyle çalışır.

---

## 📸 Ekran Görüntüleri

| Güvenli Parola (Temiz) | Sızdırılmış Parola (Tehlike) |
| :---: | :---: |
| ![Temiz Durum](docs/clean_preview.png) | ![Tehlike Durumu](docs/leak_preview.png) |

---

## 🔐 k-Anonymity Modeli Nasıl Çalışır?

Geleneksel ve hatalı yaklaşımda kontrol edilmek istenen parola doğrudan bir sunucuya gönderilir. LeakSentry bu güvenlik riskini **k-Anonymity** mimarisiyle ortadan kaldırır:

1. **Yerel Özetleme (SHA-1):** Parola cihazınızda `SHA-1` algoritmasıyla 40 karakterlik bir hash değerine dönüştürülür.
2. **Ön Ek Gönderimi (Prefix - 5 Karakter):** Hash'in yalnızca ilk 5 karakteri HIBP Range API'sine sorgulanır. Sunucu, bu 5 karakterle başlayan binlerce olası sızmış hash listesini geri döner.
3. **Yerel Kuyruk Eşleştirme (Suffix - 35 Karakter):** Cihazda gizli tutulan 35 karakterlik kuyruk kısmı, sunucudan dönen anonim liste içinde yerel bellekte taranır.
4. **Sıfır İfşa:** Gerçek parolanız veya 40 karakterlik tam hash'iniz **asla ağ trafiğine çıkmaz**.

---

## 🚀 Kurulum

### Depoyu Klonlayın
```bash
git clone [https://github.com/mlkaydemir/LeakSentry.git](https://github.com/mlkaydemir/LeakSentry.git)
cd LeakSentry

# Kurulum

### 1. Depoyu Klonlayın

```bash
git clone <repo-url>
cd <repo-klasoru>
```

### 2. Bağımlılıkları Yükleyin

```bash
pip install -r requirements.txt
```

# Kullanım

Aracı başlatmak için terminalde aşağıdaki komutu çalıştırın:

```bash
python leak_checker.py
```

### Özellikler

* **Maskelenmiş Giriş:** Parolalar girilirken karakterler ekranda `*` olarak görüntülenir ve terminal geçmişine kaydedilmez.
* **İnteraktif Çalışma:** Programı yeniden başlatmadan birden fazla parola sorgusu gerçekleştirebilirsiniz.
* **Güvenli Çıkış:** Uygulamadan çıkmak için `q` yazıp Enter'a basın veya `CTRL + C` kısayolunu kullanın.

# Kullanılan Teknolojiler

* **Python 3.10+**
* **Rich** — Terminal panelleri, kriptografik tablolar ve durum göstergeleri için.
* **prompt_toolkit** — Maskeli parola girişi ve gelişmiş terminal etkileşimi için.
* **Requests** — HIBP Pwned Passwords Range API ile güvenli haberleşme için.
* **hashlib** *(Python Standard Library)* — Yerel SHA-1 hash üretimi için.

# Lisans

Bu proje **MIT Lisansı** altında sunulmaktadır. Ayrıntılar için `LICENSE` dosyasına göz atabilirsiniz.
