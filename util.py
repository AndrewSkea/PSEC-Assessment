import enum


class Func(enum.Enum):
    Post = 0
    Like = 1
    Share = 2
    Activate = 3


def print_step(stp):
    if len(stp) > 2:
        print("Type: {}\nPerson: {}\n{}\n".format(
            str(stp[0]), str(stp[1].name), str(stp[2])
        ))
    else:
        print("Activate")
