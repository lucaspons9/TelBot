from telegram.ext import Updater, CommandHandler, MessageHandler, Filters
from city import *
import random

def load_graph() -> CityGraph:
    """Returns the CityGraph"""
    g: CityGraph = load_city_graph("city_graph")
    return g

def load_restaurants() -> restaurants.Restaurants:
    """Returns the list of all the restaurants in Barcelona"""
    restaurants_list: restaurants.Restaurants = restaurants.load_restaurants("restaurants_list.pkl")
    return restaurants_list

def start(update, context):
    """Sends the user a welcome message back."""
    name: str = update.effective_chat.first_name
    context.bot.send_message(chat_id = update.effective_chat.id, text ="Hi %s! I'm ready to guide you to any restaurant you wish. To learn how to use this bot, please type the command /help." % name)

def help(update, context):
    """Sends the user a guide message of how to use this bot."""
    help_text: str = "To get the full experience of this bot, you can use the following commands:\n\n🔵 /author: Shows the authors of this project.\n\n🔵 /find <query>: Shows the 12 closest matching restaurants in barcelona.\n\n🔵 /info <index>: Shows the information about the restaurant the user chose.\n\n🔵 /guide <index>: First asks the user for his/her current location and, once it reads it, returns an image of the fastest way to get to the restaurant chosen, and how long it takes to get there on average.\n"
    context.bot.send_message(chat_id = update.effective_chat.id, text = help_text)

def author(update, context):
    """Sends the user a message with the names of the creators of this bot and project."""
    context.bot.send_message(chat_id = update.effective_chat.id, text ="The creators of this project are Lucas Pons and Jan Quer")

def find(update, context):
    """Returns a list of twelve restaurants that match the search of the user."""
    # We read the query the user wants to find
    query: str = context.args[0]
    restaurants_list: Restaurants = load_restaurants()
    # We get a list of restaurants from the functin find() in the module restaurants. Than, we cut the list to get the first 12 matches; if the list is shorter, this won't modify it.
    search_list: Restaurants = restaurants.find(query, restaurants_list)[:12]
    # We save the search list in the dictionary user_data.
    context.user_data['restaurants_list'] = search_list
    # We create the text that the bot will send as a message to the user by merging all the elements of the search_list into one string (answer).
    answer: str = "What restaurant are you looking for?\n"
    for i in range(0, len(search_list)):
        answer += str(i + 1) + " - " + search_list[i].name + "\n"
    # The bot sends as a message the list of the first twelve restaurants that match the search.
    context.bot.send_message(chat_id = update.effective_chat.id, text = answer)

def info(update, context):
    "Returns the information about the restaurant selected by the user from the list given"
    # We read the index the user wants information about.
    index: int = int(context.args[0])
    # We check that the user has first entered a /find command.
    if 'restaurants_list' not in context.user_data.keys():
        context.bot.send_message(chat_id = update.effective_chat.id, text = "Please enter the command /find to allow me to search the matching restaurants.")
        return
    # We upload the search_list from the user_data; each user will have it's own list.
    search_list: Restaurants = context.user_data['restaurants_list']
    if index > 12 or index > len(search_list):
        context.bot.send_message(chat_id = update.effective_chat.id, text = "Please choose a restaurant index between 1 and 12.")
        return
    # We create the text that the bot will send as a message (answer) to the user by merging all the attributes of the chosen restaurant.
    answer: str = "This is the information about " + search_list[index - 1].name + ":\n"
    answer += " - Street: " + search_list[index - 1].street + "\n"
    answer += " - Filter: " + search_list[index - 1].secondary_filters + "\n"
    context.bot.send_message(chat_id = update.effective_chat.id, text =answer)

def guide(update, context):
    """Sends the user an image of the route from his/her current location to the restaurant selected"""
    index: int = int(context.args[0])
    if 'restaurants_list' not in context.user_data.keys():
        context.bot.send_message(chat_id = update.effective_chat.id, text ="Please find restaurants.")
        return
    search_list: Restaurants = context.user_data['restaurants_list']
    if index > 12 or index > len(search_list):
        context.bot.send_message(chat_id = update.effective_chat.id, text ="Please choose a restaurant index between 1 and 12.")
        return
    context.user_data['restaurant_position'] = search_list[index - 1].position
    context.bot.send_message(chat_id = update.effective_chat.id, text ="I will guide you to %s, you just need to share your location!" % search_list[index - 1].name)

def path(update, context):
    try:
        # We get the position of the user
        user_position: Coord = (update.message.location.longitude, update.message.location.latitude)
        # We get the position of the restaurant.
        restaurant_position: Coord = context.user_data["restaurant_position"]
        # We build the path with the functino find_path() from city.py
        path: Path = find_path(load_osmnx_graph("barcelona_walk") ,load_graph(), user_position, restaurant_position)
        total_time: int = int(find_time_path(load_graph(), path))
        # We create a random name for the filename since, at the end of the function, the file will be deleted
        filename: str = "%d.png" % random.randint(1000000, 9999999)
        # We create the map, saved as filename, where the path from the user's location to the restaurant is painted.
        plot_path(load_graph(), path, filename, user_position, restaurant_position)
        # The bot sends the map to the user.
        context.bot.send_photo(chat_id = update.effective_chat.id, photo = open(filename, 'rb'))
        context.bot.send_message(chat_id = update.effective_chat.id, text = "Trip will be of approx %d minutes." % total_time)
        # We delete the map.
        os.remove(filename)
    except Exception as e:
        print(e)
        context.bot.send_message(chat_id = update.effective_chat.id, text = '💣')

def start_bot():
    # declara una constant amb el access token que llegeix de token.txt
    TOKEN = open('token.txt').read().strip()
    # crea objectes per treballar amb Telegram
    updater = Updater(token=TOKEN, use_context =True)
    dispatcher = updater.dispatcher
    # indica que quan el bot rebi la comanda /start s'executi la funció start

    commands: Dict[str, str] = {'start' : start, 'help': help, 'author': author, 'find': find, 'info': info, 'guide': guide}
    for command in commands.keys():
        dispatcher.add_handler(CommandHandler(command, commands[command]))

    dispatcher.add_handler(MessageHandler(Filters.location, path))
    # engega el bot
    updater.start_polling()
    updater.idle()

def main():
    g: CityGraph = load_graph()
    restaurants_list: restaurants.Restaurants = load_restaurants()
    print("done uploading")
    start_bot()

main()
